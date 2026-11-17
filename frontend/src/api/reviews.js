import { apiRequest } from "./apiRequest.js";

export function fetchTruckReviews(truckId) {
  return apiRequest(`/api/trucks/${truckId}/reviews/`);
}

export function submitTruckReview(truckId, { rating, comment, photoUrl }) {
  return apiRequest(`/api/trucks/${truckId}/reviews/`, {
    method: "POST",
    body: {
      rating,
      comment,
      photo_url: photoUrl || "",
    },
  });
}

export async function uploadReviewPhotoToCloudinary(file) {
  const cloudName = import.meta.env.VITE_CLOUDINARY_CLOUD_NAME;
  const uploadPreset = import.meta.env.VITE_CLOUDINARY_UPLOAD_PRESET;

  if (!cloudName || !uploadPreset) {
    throw new Error("Cloudinary is not configured in .env.");
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("upload_preset", uploadPreset);

  const response = await fetch(
    `https://api.cloudinary.com/v1_1/${cloudName}/image/upload`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    throw new Error("Photo upload failed. Please try again.");
  }

  const data = await response.json();
  return data.secure_url;
}
