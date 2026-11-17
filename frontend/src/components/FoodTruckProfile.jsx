import Drawer from "@mui/material/Drawer";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Rating from "@mui/material/Rating";
import Stack from "@mui/material/Stack";
import CloseIcon from "@mui/icons-material/Close";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import FoodTruckMenu from "./FoodTruckMenu.jsx";
import FoodTruckReviews from "./FoodTruckReviews.jsx";

export default function FoodTruckProfile({
  truck,
  open,
  onClose,
  onReviewSubmitted,
}) {
  const properties = truck?.properties;

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: { xs: "100%", sm: 420 },
          maxWidth: "100%",
        },
      }}
    >
      <Box sx={{ p: 3 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mb: 2,
          }}
        >
          <Typography variant="h6">Food Truck Profile</Typography>
          <IconButton onClick={onClose} aria-label="Close profile">
            <CloseIcon />
          </IconButton>
        </Box>

        {properties && (
          <>
            <Box sx={{ textAlign: "center", mb: 3 }}>
              <LocalShippingIcon sx={{ fontSize: 64, color: "primary.main" }} />

              <Typography variant="h5" sx={{ mt: 1 }}>
                {properties.name}
              </Typography>

              <Typography color="text.secondary">
                {properties.cuisine || "Food Truck"}
              </Typography>

              <Chip
                label={properties.is_open ? "Open Now" : "Closed"}
                color={properties.is_open ? "success" : "default"}
                sx={{ mt: 2 }}
              />
            </Box>

            <Divider sx={{ mb: 3 }} />

            <Typography variant="h6" gutterBottom>
              About
            </Typography>

            <Typography color="text.secondary" sx={{ mb: 3 }}>
              {properties.description || "No description available."}
            </Typography>

            <Divider sx={{ mb: 3 }} />

            <FoodTruckMenu truckId={truck.id} />

            <Divider sx={{ my: 3 }} />

            <FoodTruckReviews
              truckId={truck.id}
              onReviewSubmitted={onReviewSubmitted}
            />
          </>
        )}
      </Box>
    </Drawer>
  );
}
