from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.serializers import ProfileSerializer, ProfileUpdateSerializer


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user

        if data.get("phone_number"):
            user.phone_number = data["phone_number"]

        if data.get("new_password"):
            if not user.check_password(data.get("old_password")):
                return Response({"error": "Joriy parol noto'g'ri"}, status=400)
            user.set_password(data["new_password"])

        user.save()
        return Response(ProfileSerializer(user).data)
