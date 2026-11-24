from hope_api_auth.views import TokenRequiredViewSet

from hope_documents.grants import Grant
from hope_documents.models import User

from ..serializers import UserSerializer


class UserViewSet(TokenRequiredViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission = Grant.API_PLAN_MANAGE
