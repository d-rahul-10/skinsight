export const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
export const ACCEPTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.jpe', '.png', '.webp'];

export function validateImageFile(file: File): string | null {
  const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
  const supported = ACCEPTED_IMAGE_TYPES.includes(file.type.toLowerCase()) || ACCEPTED_IMAGE_EXTENSIONS.includes(extension);
  if (!supported) return 'Choose a JPG, JPEG, PNG, or WEBP image.';
  if (file.size <= 0) return 'This file is empty. Choose a readable image.';
  if (file.size > MAX_UPLOAD_BYTES) return 'Images must be 8 MB or smaller.';
  return null;
}
