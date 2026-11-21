import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActions from "@mui/material/CardActions";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import MyLocationIcon from "@mui/icons-material/MyLocation";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";

import {
  checkInFoodTruck,
  checkOutFoodTruck,
  fetchMyFoodTrucks,
  updateFoodTruckCoverPhoto,
} from "../api/foodTrucks.js";
import { uploadReviewPhotoToCloudinary } from "../api/reviews.js";
import { useAuth } from "../hooks/useAuth.js";

const DEFAULT_OPEN_HOURS = 3;

/** "HH:MM" string for a time DEFAULT_OPEN_HOURS from now, rounded up to the half hour. */
function defaultClosingTimeText() {
  const closingTime = new Date(
    Date.now() + DEFAULT_OPEN_HOURS * 60 * 60 * 1000,
  );
  closingTime.setMinutes(closingTime.getMinutes() <= 30 ? 30 : 60, 0, 0);
  return closingTime.toTimeString().slice(0, 5);
}

/**
 * Turns the time picker's "HH:MM" into a real Date: today at that time,
 * or tomorrow if that time already passed (e.g. closing at 1:00 AM).
 */
function closingTimeTextToDate(closingTimeText) {
  const [hours, minutes] = closingTimeText.split(":").map(Number);
  const closingDate = new Date();
  closingDate.setHours(hours, minutes, 0, 0);
  if (closingDate <= new Date()) {
    closingDate.setDate(closingDate.getDate() + 1);
  }
  return closingDate;
}

/** Wraps the browser's callback-style geolocation API in a Promise. */
function getCurrentPhonePosition() {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("This browser does not support location services."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => resolve(position.coords),
      (positionError) =>
        reject(
          new Error(`Could not get your location: ${positionError.message}`),
        ),
      // maximumAge: accept a reading up to 30s old. The map already tracks the
      // phone's position, so this is usually instant; forcing a brand-new fix
      // (maximumAge 0) can take many seconds indoors. 30s is plenty fresh for a parked truck.
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 },
    );
  });
}

/** "until 2:30 PM" label for an ISO timestamp from the API. */
function formatOpenUntil(openUntilText) {
  if (!openUntilText) return "";
  return `until ${new Date(openUntilText).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
}

export default function OwnerPanel({ isOpen, onClose, onTrucksChanged }) {
  // Shared login state; the login form itself is the app-wide account dialog
  const { currentUser, logOut, openAccountDialog } = useAuth();
  const currentUsername = currentUser?.username ?? null;
  // Remembers whose trucks were loaded, so a different user never sees them
  const [loadedTrucks, setLoadedTrucks] = useState({
    username: null,
    features: [],
  });
  const [closingTimeText, setClosingTimeText] = useState(
    defaultClosingTimeText,
  );
  const [busyTruckId, setBusyTruckId] = useState(null);
  const [statusMessage, setStatusMessage] = useState(null); // { severity, text }

  const hasLoadedMyTrucks =
    currentUsername !== null && loadedTrucks.username === currentUsername;
  const myFoodTruckFeatures = hasLoadedMyTrucks ? loadedTrucks.features : [];

  const loadMyFoodTrucks = useCallback(async (username) => {
    const featureCollection = await fetchMyFoodTrucks();
    setLoadedTrucks({ username, features: featureCollection.features });
  }, []);

  // Load the trucks when the panel opens, and again whenever a different user logs in
  useEffect(() => {
    if (!isOpen || currentUsername === null) return;
    let isCurrentEffect = true; // ignore a slow answer for a user who already logged out
    fetchMyFoodTrucks()
      .then((featureCollection) => {
        if (isCurrentEffect) {
          setLoadedTrucks({
            username: currentUsername,
            features: featureCollection.features,
          });
        }
      })
      .catch((requestError) => {
        if (isCurrentEffect) {
          setStatusMessage({ severity: "error", text: requestError.message });
        }
      });
    return () => {
      isCurrentEffect = false;
    };
  }, [isOpen, currentUsername]);

  async function handleLogOut() {
    setStatusMessage(null);
    try {
      await logOut();
    } catch (requestError) {
      setStatusMessage({ severity: "error", text: requestError.message });
    }
  }

  /** Runs a check-in, check-out, or photo update, then refreshes this panel and the customer map. */
  async function runTruckAction(truckId, truckAction, successText) {
    setBusyTruckId(truckId);
    setStatusMessage(null);
    try {
      await truckAction();
      await loadMyFoodTrucks(currentUsername);
      onTrucksChanged(); // refresh the map right away instead of waiting 30 seconds
      setStatusMessage({ severity: "success", text: successText });
    } catch (requestError) {
      setStatusMessage({ severity: "error", text: requestError.message });
    } finally {
      setBusyTruckId(null);
    }
  }

  function handleCheckIn(truckFeature) {
    const openUntil = closingTimeTextToDate(closingTimeText);
    return runTruckAction(
      truckFeature.id,
      async () => {
        const phoneCoordinates = await getCurrentPhonePosition();
        await checkInFoodTruck({
          truckId: truckFeature.id,
          latitude: phoneCoordinates.latitude,
          longitude: phoneCoordinates.longitude,
          openUntil,
        });
      },
      `${truckFeature.properties.name} is open ${formatOpenUntil(openUntil.toISOString())}.`,
    );
  }

  function handleCheckOut(truckFeature) {
    return runTruckAction(
      truckFeature.id,
      () => checkOutFoodTruck({ truckId: truckFeature.id }),
      `${truckFeature.properties.name} is now closed.`,
    );
  }

  function handleCoverPhotoChange(truckFeature, event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    return runTruckAction(
      truckFeature.id,
      async () => {
        const uploadedUrl = await uploadReviewPhotoToCloudinary(file);
        await updateFoodTruckCoverPhoto({
          truckId: truckFeature.id,
          coverPhotoUrl: uploadedUrl,
        });
      },
      `Updated cover photo for ${truckFeature.properties.name}.`,
    );
  }

  return (
    <Drawer anchor="right" open={isOpen} onClose={onClose}>
      <Box sx={{ width: { xs: "100vw", sm: 400 }, padding: 2 }}>
        <Stack
          direction="row"
          sx={{
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 2,
          }}
        >
          <Typography variant="h6">Owner check-in</Typography>
          <Button onClick={onClose}>Done</Button>
        </Stack>

        {statusMessage && (
          <Alert severity={statusMessage.severity} sx={{ marginBottom: 2 }}>
            {statusMessage.text}
          </Alert>
        )}

        {currentUser === undefined && (
          <Typography color="text.secondary">Loading...</Typography>
        )}

        {currentUser === null && (
          <Stack spacing={2}>
            <Typography color="text.secondary">
              Truck owners: log in to check in your truck.
            </Typography>
            <Button
              variant="contained"
              onClick={() => openAccountDialog("login")}
            >
              Log in
            </Button>
          </Stack>
        )}

        {currentUser && (
          <Stack spacing={2}>
            <Stack
              direction="row"
              sx={{ justifyContent: "space-between", alignItems: "center" }}
            >
              <Typography color="text.secondary">
                Logged in as {currentUser.username}
              </Typography>
              <Button size="small" onClick={handleLogOut}>
                Log out
              </Button>
            </Stack>

            <TextField
              label="Open until"
              type="time"
              value={closingTimeText}
              onChange={(event) => setClosingTimeText(event.target.value)}
              helperText="A time earlier than now means tomorrow (e.g. closing at 1:00 AM)."
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <Divider />

            {hasLoadedMyTrucks && myFoodTruckFeatures.length === 0 && (
              <Typography color="text.secondary">
                No trucks are linked to this account yet. In the admin, set this
                user as a truck&apos;s owner.
              </Typography>
            )}

            {myFoodTruckFeatures.map((truckFeature) => {
              const truckProperties = truckFeature.properties;
              const isBusy = busyTruckId === truckFeature.id;
              return (
                <Card key={truckFeature.id} variant="outlined">
                  {truckProperties.cover_photo_url && (
                    <Box
                      component="img"
                      src={truckProperties.cover_photo_url}
                      alt={`${truckProperties.name} cover`}
                      sx={{
                        width: "100%",
                        height: 140,
                        objectFit: "cover",
                        display: "block",
                      }}
                    />
                  )}
                  <CardContent>
                    <Stack
                      direction="row"
                      sx={{
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <Typography variant="subtitle1">
                        {truckProperties.name}
                      </Typography>
                      <Chip
                        size="small"
                        label={
                          truckProperties.is_open
                            ? `Open ${formatOpenUntil(truckProperties.open_until)}`
                            : "Closed"
                        }
                        color={truckProperties.is_open ? "success" : "default"}
                        variant={
                          truckProperties.is_open ? "filled" : "outlined"
                        }
                      />
                    </Stack>
                  </CardContent>
                  <CardActions sx={{ flexWrap: "wrap", gap: 1 }}>
                    <Button
                      variant="contained"
                      startIcon={<MyLocationIcon />}
                      disabled={isBusy}
                      onClick={() => handleCheckIn(truckFeature)}
                    >
                      {isBusy ? "Working..." : "I'm here"}
                    </Button>
                    {truckProperties.is_open && (
                      <Button
                        disabled={isBusy}
                        onClick={() => handleCheckOut(truckFeature)}
                      >
                        Close now
                      </Button>
                    )}
                    <Button
                      component="label"
                      size="small"
                      startIcon={<PhotoCameraIcon />}
                      disabled={isBusy}
                    >
                      {truckProperties.cover_photo_url
                        ? "Change Cover"
                        : "Cover Photo"}
                      <input
                        type="file"
                        accept="image/*"
                        hidden
                        onChange={(event) =>
                          handleCoverPhotoChange(truckFeature, event)
                        }
                      />
                    </Button>
                  </CardActions>
                </Card>
              );
            })}
          </Stack>
        )}
      </Box>
    </Drawer>
  );
}
