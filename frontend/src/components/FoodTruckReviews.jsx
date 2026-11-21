import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Rating from "@mui/material/Rating";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";

import {
  deleteTruckReview,
  fetchTruckReviews,
  submitTruckReview,
  updateTruckReview,
  uploadReviewPhotoToCloudinary,
} from "../api/reviews.js";
import { useAuth } from "../hooks/useAuth.js";

export default function FoodTruckReviews({ truckId, onReviewSubmitted }) {
  // undefined = still checking, null = logged out, object = logged in
  const { currentUser, openAccountDialog } = useAuth();
  const [reviews, setReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // New review form state
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [photoFile, setPhotoFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Inline edit state
  const [editingReviewId, setEditingReviewId] = useState(null);
  const [editRating, setEditRating] = useState(5);
  const [editComment, setEditComment] = useState("");
  const [editPhotoUrl, setEditPhotoUrl] = useState("");
  const [editPhotoFile, setEditPhotoFile] = useState(null);
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [deletingReviewId, setDeletingReviewId] = useState(null);

  const [errorMessage, setErrorMessage] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    let isCurrent = true;
    setIsLoading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    setEditingReviewId(null);

    fetchTruckReviews(truckId)
      .then((reviewsData) => {
        if (isCurrent) setReviews(reviewsData);
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

  function startEditing(review) {
    setEditingReviewId(review.id);
    setEditRating(review.rating);
    setEditComment(review.comment || "");
    setEditPhotoUrl(review.photo_url || "");
    setEditPhotoFile(null);
    setErrorMessage(null);
    setSuccessMessage(null);
  }

  function cancelEditing() {
    setEditingReviewId(null);
    setEditPhotoFile(null);
  }

  async function handleSaveEdit(reviewId) {
    if (!editRating) {
      setErrorMessage("Please pick a star rating.");
      return;
    }

    setIsSavingEdit(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      let finalPhotoUrl = editPhotoUrl;
      if (editPhotoFile) {
        finalPhotoUrl = await uploadReviewPhotoToCloudinary(editPhotoFile);
      }

      const updatedReview = await updateTruckReview(truckId, reviewId, {
        rating: editRating,
        comment: editComment,
        photoUrl: finalPhotoUrl,
      });

      setReviews((previousReviews) =>
        previousReviews.map((item) =>
          item.id === reviewId ? updatedReview : item,
        ),
      );
      setEditingReviewId(null);
      setEditPhotoFile(null);
      setSuccessMessage("Review updated!");

      if (onReviewSubmitted) {
        onReviewSubmitted();
      }
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setIsSavingEdit(false);
    }
  }

  async function handleDelete(reviewId) {
    setDeletingReviewId(reviewId);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await deleteTruckReview(truckId, reviewId);
      setReviews((previousReviews) =>
        previousReviews.filter((item) => item.id !== reviewId),
      );
      if (editingReviewId === reviewId) {
        setEditingReviewId(null);
      }
      setSuccessMessage("Review deleted.");

      if (onReviewSubmitted) {
        onReviewSubmitted();
      }
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setDeletingReviewId(null);
    }
  }

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Reviews ({reviews.length})
      </Typography>

      {/* Logged out: a button that opens the Log in / Sign up dialog instead of the form */}
      {!currentUser && (
        <Box sx={{ mb: 3 }}>
          {errorMessage && (
            <Alert severity="error" sx={{ mb: 1.5 }}>
              {errorMessage}
            </Alert>
          )}
          {currentUser === null && (
            <Button
              variant="outlined"
              size="small"
              fullWidth
              onClick={() => openAccountDialog("login")}
            >
              Log in to leave a review
            </Button>
          )}
        </Box>
      )}

      {/* Review submission form (logged-in users only) */}
      {currentUser && (
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

          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            sx={{ mb: 1.5 }}
          >
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
      )}

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
          {reviews.map((review) => {
            const canModify =
              currentUser &&
              (currentUser.is_staff ||
                currentUser.username === review.username);
            const isEditing = editingReviewId === review.id;

            return (
              <Box key={review.id}>
                {isEditing ? (
                  <Stack spacing={1.5}>
                    <Typography variant="subtitle2">
                      Edit your review
                    </Typography>
                    <Rating
                      value={editRating}
                      onChange={(_event, newRating) => setEditRating(newRating)}
                    />
                    <TextField
                      fullWidth
                      multiline
                      minRows={2}
                      size="small"
                      label="Comment"
                      value={editComment}
                      onChange={(event) => setEditComment(event.target.value)}
                    />
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Button
                        component="label"
                        variant="outlined"
                        size="small"
                        startIcon={<PhotoCameraIcon />}
                      >
                        {editPhotoFile || editPhotoUrl
                          ? "Replace Photo"
                          : "Add Photo"}
                        <input
                          type="file"
                          accept="image/*"
                          hidden
                          onChange={(event) =>
                            setEditPhotoFile(event.target.files?.[0] || null)
                          }
                        />
                      </Button>
                      {(editPhotoUrl || editPhotoFile) && (
                        <Button
                          size="small"
                          color="inherit"
                          onClick={() => {
                            setEditPhotoUrl("");
                            setEditPhotoFile(null);
                          }}
                        >
                          Remove Photo
                        </Button>
                      )}
                    </Stack>
                    {editPhotoFile && (
                      <Typography variant="caption" color="text.secondary">
                        New photo: {editPhotoFile.name}
                      </Typography>
                    )}
                    <Stack direction="row" spacing={1}>
                      <Button
                        variant="contained"
                        size="small"
                        disabled={isSavingEdit}
                        onClick={() => handleSaveEdit(review.id)}
                      >
                        {isSavingEdit ? "Saving..." : "Save"}
                      </Button>
                      <Button
                        size="small"
                        disabled={isSavingEdit}
                        onClick={cancelEditing}
                      >
                        Cancel
                      </Button>
                    </Stack>
                  </Stack>
                ) : (
                  <>
                    <Stack
                      direction="row"
                      spacing={1}
                      justifyContent="space-between"
                      alignItems="center"
                    >
                      <Typography variant="subtitle2">
                        {review.username}
                      </Typography>
                      <Stack direction="row" spacing={0.5} alignItems="center">
                        <Rating value={review.rating} readOnly size="small" />
                        {canModify && (
                          <>
                            <IconButton
                              size="small"
                              aria-label="Edit review"
                              onClick={() => startEditing(review)}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                            <IconButton
                              size="small"
                              aria-label="Delete review"
                              color="error"
                              disabled={deletingReviewId === review.id}
                              onClick={() => handleDelete(review.id)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </>
                        )}
                      </Stack>
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
                  </>
                )}
              </Box>
            );
          })}
        </Stack>
      )}
    </Box>
  );
}
