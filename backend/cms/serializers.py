from rest_framework import serializers


class HomeBannerOut(serializers.Serializer):
    id = serializers.IntegerField()
    image = serializers.URLField()  # absolute URL
    title = serializers.CharField(allow_blank=True)
    alt = serializers.CharField(allow_blank=True)
    href = serializers.URLField(allow_blank=True, required=False)
    # Optional: surfaced if you later include them from the model
    createdAt = serializers.DateTimeField(required=False)
    updatedAt = serializers.DateTimeField(required=False)


class HomeRailOut(serializers.Serializer):
    title = serializers.CharField()
    viewAll = serializers.CharField(allow_blank=True)
    # Optional: if you want to return rail id/order later
    id = serializers.IntegerField(required=False)
    sort = serializers.IntegerField(required=False)
    # Keeping items optional/empty for now; can be hydrated later
    items = serializers.ListField(child=serializers.DictField(), required=False)


class HomeContentOut(serializers.Serializer):
    banners = HomeBannerOut(many=True)
    rails = HomeRailOut(many=True, required=False)
