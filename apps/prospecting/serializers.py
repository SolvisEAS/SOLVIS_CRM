from rest_framework import serializers

from core.tenancy import TenantScopedSerializerMixin

from .models import Prospect, ProspectingSettings, Search, SearchRun


class SearchRunSerializer(serializers.ModelSerializer):
    search_name = serializers.CharField(source="search.name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SearchRun
        fields = (
            "id", "search", "search_name", "status", "status_label", "model", "created_at", "started_at",
            "finished_at", "date_from", "date_to", "found_count", "new_count", "duplicate_count",
            "out_of_range_count", "web_searches", "input_tokens", "output_tokens", "cost_usd", "summary", "error",
        )
        read_only_fields = fields


class SearchSerializer(serializers.ModelSerializer):
    prospects_count = serializers.IntegerField(read_only=True)
    last_run = serializers.SerializerMethodField()

    class Meta:
        model = Search
        fields = (
            "id", "name", "keywords", "offering", "countries", "period_days", "depth", "is_active",
            "prospects_count", "last_run", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_last_run(self, obj):
        run = obj.runs.order_by("-created_at").first()
        return SearchRunSerializer(run).data if run else None

    def validate_keywords(self, value):
        lines = [k.strip() for k in value.splitlines() if k.strip()]
        if not lines:
            raise serializers.ValidationError("Escribí al menos una frase para buscar.")
        return "\n".join(lines)

    def validate_period_days(self, value):
        if not 1 <= value <= 365:
            raise serializers.ValidationError("El período tiene que ser de 1 a 365 días.")
        return value


class ProspectSerializer(TenantScopedSerializerMixin, serializers.ModelSerializer):
    search_name = serializers.CharField(source="search.name", read_only=True, default="")
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    has_contact = serializers.BooleanField(read_only=True)
    converted_opportunity = serializers.IntegerField(source="lead.converted_opportunity_id", read_only=True,
                                                     default=None)
    converted_contact = serializers.IntegerField(source="lead.converted_contact_id", read_only=True, default=None)

    class Meta:
        model = Prospect
        fields = (
            "id", "search", "search_name", "run", "name", "company", "need", "quote", "source_url", "source_name",
            "published_at", "location", *Prospect.CONTACT_FIELDS, "has_contact", "score", "score_reason",
            "status", "status_label", "notes", "assigned_to", "contacted_at", "lead", "converted_contact",
            "converted_opportunity", "created_at", "updated_at",
        )
        read_only_fields = ("id", "search", "run", "contacted_at", "lead", "created_at", "updated_at")

    def validate_status(self, value):
        current = self.instance.status if self.instance else None
        if value == Prospect.Status.CONVERTIDO and current != value:
            raise serializers.ValidationError("Para convertirlo usá el botón Convertir.")
        if current == Prospect.Status.CONVERTIDO and value != current:
            raise serializers.ValidationError("Este prospecto ya fue convertido.")
        return value

    def validate_score(self, value):
        return max(0, min(100, value))


class SettingsSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=True)
    clear_api_key = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = ProspectingSettings
        fields = ("model", "monthly_budget_usd", "api_key", "clear_api_key")

    def validate_monthly_budget_usd(self, value):
        if value < 0:
            raise serializers.ValidationError("El tope no puede ser negativo.")
        return value

    def update(self, instance, validated_data):
        key = validated_data.pop("api_key", "")
        if validated_data.pop("clear_api_key", False):
            instance.anthropic_api_key = ""
        elif key:
            instance.anthropic_api_key = key
        return super().update(instance, validated_data)
