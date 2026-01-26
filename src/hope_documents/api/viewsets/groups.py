from django.contrib.auth.models import Group
from rest_framework import permissions, viewsets

from hope_documents.api.serializers import GroupSerializer


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
