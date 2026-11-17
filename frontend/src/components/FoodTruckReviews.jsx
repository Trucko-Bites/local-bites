import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import Rating from "@mui/material/Rating";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";

import {
  fetchTruckReviews,
  submitTruckReview,
  uploadReviewPhotoToCloudinary,
} from "../api/reviews.js";

export default function FoodTruckReviews({ truckId, onReviewSubmitted }) {
  const [reviews, setReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [photoFile, setPhotoFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    let isCurrent = true;
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    fetchTruckReviews(truckId)
      .then((data) => {
        if (isCurrent) setReviews(data);
      })
      .catch((error) => {
        if (isCurrent) setErrorMessage(error.message);
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [truckId]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!rating) {
      setErrorMessage("Please pick a star rating.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      let photoUrl = "";
      if (photoFile) {
        photoUrl = await uploadReviewPhotoToCloudinary(photoFile);
      }

      const savedReview = await submitTruckReview(truckId, {
        rating,
        comment,
        photoUrl,
      });

      // Put the new/updated review at the top without duplicates
      setReviews((previousReviews) => [
        savedReview,
        ...previousReviews.filter((item) => item.id !== savedReview.id),
      ]);
      setComment("");
      setPhotoFile(null);
      setSuccessMessage("Review posted!");

      if (onReviewSubmitted) {
        onReviewSubmitted();
      }
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Reviews ({reviews.length})
      </Typography>

      {/* Review submission form */}
      <Box component="form" onSubmit={handleSubmit} sx={{ mb: 3 }}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Rate this truck
        </Typography>
        <Rating
          name="truck-rating"
          value={rating}
          onChange={(_event, newRating) => setRating(newRating)}
          sx={{ mb: 1.5 }}
        />

        <TextField
          fullWidth
          multiline
          minRows={2}
          size="small"
          label="Share what you ordered..."
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          sx={{ mb: 1.5 }}
        />

        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
          <Button
            component="label"
            variant="outlined"
            size="small"
            startIcon={<PhotoCameraIcon />}
          >
            {photoFile ? "Change Photo" : "Add Photo"}
            <input
              type="file"
              accept="image/*"
              hidden
              onChange={(event) =>
                setPhotoFile(event.target.files?.[0] || null)
              }
            />
          </Button>
          {photoFile && (
            <Typography variant="caption" color="text.secondary" noWrap>
              {photoFile.name}
            </Typography>
          )}
        </Stack>

        {errorMessage && (
          <Alert severity="error" sx={{ mb: 1.5 }}>
            {errorMessage}
          </Alert>
        )}
        {successMessage && (
          <Alert severity="success" sx={{ mb: 1.5 }}>
            {successMessage}
          </Alert>
        )}

        <Button
          type="submit"
          variant="contained"
          size="small"
          disabled={isSubmitting}
          fullWidth
        >
          {isSubmitting ? "Posting..." : "Post Review"}
        </Button>
      </Box>

      {/* Existing reviews list */}
      {isLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
          <CircularProgress size={24} />
        </Box>
      ) : reviews.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No reviews yet. Be the first to rate this truck!
        </Typography>
      ) : (
        <Stack spacing={2} divider={<Divider />}>
          {reviews.map((review) => (
            <Box key={review.id}>
              <Stack
                direction="row"
                spacing={1}
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography variant="subtitle2">{review.username}</Typography>
                <Rating value={review.rating} readOnly size="small" />
              </Stack>

              {review.comment && (
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  {review.comment}
                </Typography>
              )}

              {review.photo_url && (
                <Box
                  component="img"
                  src={review.photo_url}
                  alt={`Food photo by ${review.username}`}
                  sx={{
                    mt: 1,
                    width: "100%",
                    maxHeight: 200,
                    objectFit: "cover",
                    borderRadius: 1,
                  }}
                />
              )}
            </Box>
          ))}
        </Stack>
      )}
    </Box>
  );
}
