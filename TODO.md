# EcoBank TODO List

This document outlines crucial missing features, potential improvements, and identified risks for the EcoBank application, based on a comprehensive review.

## 1. Critical Operational Gaps & Security Risks

*   [x] **Email Verification & Password Reset:**
    *   **Issue:** No email verification during registration, allowing invalid email addresses. No "Forgot Password" functionality, leading to account loss and potential loss of encrypted Hive keys if user forgets password.
    *   **Action:** Implement email verification for new registrations. Develop a secure password reset flow.
*   [x] **Hive Key Security Architecture:**
    *   **Issue:** All user Hive keys are encrypted with a single, server-side `HIVE_ENCRYPTION_KEY`.
    *   **Risk:** A single server compromise could expose all user Hive accounts. This is a significant security vulnerability.
    *   **Action:** Explore client-side encryption, per-user encryption keys derived from their login password, or clear user warnings about the custodial nature of key storage.
    *   **Update:** Implemented "Download Keys" and "Delete Account" flows to allow users to offboard. Restricted imports to exclude Owner keys.
*   [x] **PayPal Transaction Atomicity & Race Conditions:**
    *   **Issue:** Potential for race conditions in `capture_order` (client-side) and `paypal_webhook` (server-side) leading to double crediting. Deducting credits before Hive blockchain confirmation introduces a risk of credit loss if Hive transaction fails.
    *   **Action:** Implement robust idempotency checks for PayPal credit processing. Introduce a "pending" state for credit deductions linked to Hive account creation, with automated rollback/refund for failed blockchain transactions.

## 2. Hive Specific Enhancements

*   [x] **Resource Credits (RC) Delegation:**
    *   **Issue:** Newly created Hive accounts (via EcoBank) have insufficient Resource Credits to perform basic operations (posting, commenting, voting). This renders new accounts unusable without external RC delegation.
    *   **Action:** Implement automatic delegation of a small amount of Hive Power (HP) from the `HIVE_CLAIMER_ACCOUNT` to newly created user accounts to provide initial RC.
*   [x] **Posting Options & Monetization:**
    *   **Issue:** Limited posting options. Default tags might not suit user needs. No support for beneficiaries.
    *   **Action:** Implement flexible tag selection for drafts. Add an option to set beneficiaries for posts (e.g., to implement platform fees).
*   [x] **Image Uploads for Posts:**
    *   **Issue:** Markdown editor is text-only. Users cannot directly upload images, limiting content creation.
    *   **Action:** Integrate an image hosting solution (e.g., ImageKit, Imgur, or self-hosted) with the markdown editor for direct image uploads.

## 3. Group & Collaboration Enhancements

*   [x] **Draft History / Versioning:**
    *   **Issue:** No version control for collaborative drafts. Concurrent edits may lead to data loss.
    *   **Action:** Implement a basic versioning system for drafts, potentially using a MongoDB document store to save historical versions.
*   [x] **Notifications:**
    *   **Issue:** Users receive no notifications for group invites, draft edits by collaborators, or successful post publications.
    *   **Action:** Implement an in-app notification system for key collaborative events.

## 4. Admin & System Management

*   [x] **Account Claim Ticket Management:**
    *   **Issue:** Admin can see pending claimed accounts, but there's no direct way to replenish them.
    *   **Action:** Add an admin action/button to trigger claiming of new accounts by the `HIVE_CLAIMER_ACCOUNT`.
*   [x] **Error Logging & Monitoring:**
    *   **Issue:** Basic logging is present, but no centralized error tracking or performance monitoring.
    *   **Action:** Integrate with a tool like Sentry or similar for production monitoring.
    *   **Update:** Implemented robust rotating file-based logging in `logs/ecobank.log` instead of external Sentry integration.
*   [x] **Scheduled Tasks:**
    *   **Issue:** No explicit scheduler for tasks like checking PayPal order status updates, RC delegation expiration, etc.
    *   **Action:** Implement a task scheduler (e.g., Celery Beat or a simple cron script) for background operations.

This TODO list will serve as a roadmap for improving the EcoBank application.