from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from backend.coreapp.middleware import Request
from backend.coreapp.models import Profile

from backend.coreapp.serializers import serialize_profile
from ..github import GitHubUser

class CurrentUser(APIView):
    """
    View to access the current user profile.
    """

    def get(self, request: Request):
        user = serialize_profile(request, request.profile)
        assert user["is_you"] == True
        return Response(user)

    def post(self, request: Request):
        """
        Login if the 'code' parameter is provided. Log out otherwise.
        """

        if "code" in request.data:
            GitHubUser.login(request, request.data["code"])

            return Response(serialize_profile(request, request.profile))
        else:
            logout(request)

            profile = Profile()
            profile.save()
            request.profile = profile
            request.session["profile_id"] = request.profile.id

            return Response(serialize_profile(request, request.profile))

@api_view(["GET"])
def user(request, username):
    """
    Gets a user's basic data
    """

    return Response(serialize_profile(request, get_object_or_404(Profile, user__username=username)))

