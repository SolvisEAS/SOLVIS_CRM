from rest_framework import serializers

from .models import TimelineEvent


class TimelineEventSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = TimelineEvent
        fields = ("id", "related_type", "related_id", "verb", "description", "user", "user_name", "created_at")
        read_only_fields = fields

    def get_user_name(self, obj):
        return (obj.user.get_full_name() or obj.user.username) if obj.user else "Sistema"
