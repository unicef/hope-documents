from django.contrib.auth.models import Group
from hope_api_auth.views import TokenRequiredViewSet

from hope_documents.api.serializers import GroupSerializer
from hope_documents.grants import Grant


class GroupViewSet(TokenRequiredViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission = Grant.API_PLAN_MANAGE
