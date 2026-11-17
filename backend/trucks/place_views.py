from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .place_search import PlaceSearchBusyError, PlaceSearchUnavailableError, search_places

MINIMUM_QUERY_LENGTH = 2
MAXIMUM_QUERY_LENGTH = 200


class PlaceSearchView(APIView):
    """
    GET /api/places/search/?query=Riverside, CA

    Returns {"results": [{"display_name", "latitude", "longitude"}, ...]}.
    Customers search without logging in, so anyone may call it.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        search_text = request.query_params.get("query", "").strip()
        if not MINIMUM_QUERY_LENGTH <= len(search_text) <= MAXIMUM_QUERY_LENGTH:
            return Response(
                {"detail": f"query must be {MINIMUM_QUERY_LENGTH}-{MAXIMUM_QUERY_LENGTH} characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            places = search_places(search_text)
        except PlaceSearchBusyError:
            # 429 tells the frontend to ask the user to try again in a moment
            return Response(
                {"detail": "Place search is busy. Try again in a moment."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except PlaceSearchUnavailableError:
            # 502: our server is fine, the upstream geocoder failed
            return Response(
                {"detail": "Place search is unavailable right now."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({"results": places})
