import json
from cryptography.fernet import Fernet
from flask import jsonify, request, current_app
from flask_login import current_user, login_required
from nectar import Hive
from nectar.imageuploader import ImageUploader

from app.api import bp
from app.models import GroupMember, GroupResource, HiveAccount


@bp.route("/upload_image", methods=["POST"])
@login_required
def upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # We need a context to know which hive account to use.
    # The frontend should send 'group_id' and optionally 'hive_username'
    group_id = request.form.get("group_id")
    hive_username = request.form.get("hive_username")

    if not group_id:
        return jsonify({"error": "group_id required"}), 400

    # Verify group membership
    membership = GroupMember.query.filter_by(
        group_id=group_id, user_id=current_user.id
    ).first()
    if not membership:
        return jsonify({"error": "Unauthorized"}), 403

    # Determine Hive Account to use
    # If hive_username provided, verify it's linked to group.
    # Else, pick the first linked one.
    target_username = None

    if hive_username:
        link = GroupResource.query.filter_by(
            group_id=group_id, resource_type="hive_account", resource_id=hive_username
        ).first()
        if link:
            target_username = hive_username

    if not target_username:
        # Pick first available
        link = GroupResource.query.filter_by(
            group_id=group_id, resource_type="hive_account"
        ).first()
        if link:
            target_username = link.resource_id

    if not target_username:
        return jsonify(
            {"error": "No linked Hive account found in group to sign upload"}
        ), 400

    # Get Credentials
    account_record = HiveAccount.query.filter_by(username=target_username).first()
    if not account_record:
        return jsonify({"error": "Account record not found"}), 500

    encryption_key = current_app.config.get("HIVE_ENCRYPTION_KEY")
    if not encryption_key:
        return jsonify({"error": "Server configuration error"}), 500

    try:
        fernet = Fernet(encryption_key)
        keys_json = fernet.decrypt(account_record.keys_enc.encode()).decode()
        keys_dict = json.loads(keys_json)
        posting_key = keys_dict.get("posting", {}).get("private")
    except Exception as e:
        current_app.logger.error(f"Decryption failed for {target_username}: {e}")
        return jsonify({"error": "Credential error"}), 500

    if not posting_key:
        return jsonify({"error": "Posting key not found"}), 500

    # Upload
    try:
        hive = Hive(keys=[posting_key])
        # ImageUploader(blockchain_instance=...)
        uploader = ImageUploader(blockchain_instance=hive)

        # Read file content to bytes, as ImageUploader might try to concat it with bytes
        image_data = file.read()

        # The upload method signature is: upload(self, image, account, image_name=None)
        url = uploader.upload(image_data, target_username, image_name=file.filename)

        return jsonify({"url": url["url"]})
    except Exception as e:
        current_app.logger.error(f"Image upload failed: {e}")
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@bp.route("/group/<int:group_id>/accounts")
@login_required
def get_group_accounts(group_id):
    # Verify membership
    membership = GroupMember.query.filter_by(
        group_id=group_id, user_id=current_user.id
    ).first()
    if not membership:
        return jsonify({"error": "Unauthorized"}), 403

    resources = GroupResource.query.filter_by(
        group_id=group_id, resource_type="hive_account"
    ).all()
    accounts = [r.resource_id for r in resources]
    return jsonify({"accounts": accounts})
