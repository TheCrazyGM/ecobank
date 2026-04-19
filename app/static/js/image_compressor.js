/**
 * Compresses an image file before uploading to ensure it's under typical upload limits (e.g. 10MB)
 * @param {File} file - The original image file
 * @returns {Promise<File>} A promise that resolves with the compressed File (or original if no compression needed/possible)
 */
async function compressImageClientSide(file) {
    return new Promise((resolve) => {
        if (!file || !file.type.startsWith('image/') || file.type === 'image/gif') {
            return resolve(file);
        }

        // Only compress if size > 1MB (1 * 1024 * 1024)
        const MAX_SIZE = 1024 * 1024;
        if (file.size <= MAX_SIZE) {
            return resolve(file);
        }

        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = function(event) {
            const img = new Image();
            img.src = event.target.result;
            img.onload = function() {
                let width = img.width;
                let height = img.height;
                const MAX_WIDTH = 1920;
                const MAX_HEIGHT = 1080;

                if (width > height) {
                    if (width > MAX_WIDTH) {
                        height *= MAX_WIDTH / width;
                        width = MAX_WIDTH;
                    }
                } else {
                    if (height > MAX_HEIGHT) {
                        width *= MAX_HEIGHT / height;
                        height = MAX_HEIGHT;
                    }
                }

                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                canvas.toBlob(function(blob) {
                    if (blob && blob.size < file.size) {
                        const compressedFile = new File([blob], file.name, {
                            type: 'image/jpeg',
                            lastModified: Date.now()
                        });
                        resolve(compressedFile);
                    } else {
                        resolve(file);
                    }
                }, 'image/jpeg', 0.85);
            };
            img.onerror = function() {
                resolve(file);
            };
        };
        reader.onerror = function() {
            resolve(file);
        };
    });
}
