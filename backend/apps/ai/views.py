"""
AI API: suggestions (staff only) and human decisions on recommendations.
AI output is advisory; endpoints return the recommendation id for review.
"""

from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthority
from apps.ai.models import AIRecommendation
from apps.ai.services import get_provider, record_recommendation
from apps.audit.services import log_action
from apps.incidents.models import Incident


class AISuggestView(APIView):
    """POST /api/v1/ai/incidents/<id>/suggest/ — category + severity advice."""

    permission_classes = [permissions.IsAuthenticated, IsAuthority]
    throttle_scope = "ai"  # AI calls are expensive and optional

    def post(self, request, incident_id):
        incident = Incident.objects.filter(pk=incident_id).first()
        if incident is None:
            return Response({"detail": "Incident not found."}, status=404)
        provider = get_provider()
        category_suggestion = provider.suggest_category(incident.title, incident.description)
        severity_suggestion = provider.suggest_severity(incident.description)
        recommendations = [
            record_recommendation(
                incident=incident,
                kind="category",
                output=category_suggestion,
                confidence=category_suggestion.get("confidence"),
            ),
            record_recommendation(
                incident=incident,
                kind="severity",
                output=severity_suggestion,
                confidence=severity_suggestion.get("confidence"),
            ),
        ]
        return Response(
            {
                "disclaimer": "AI suggestions are advisory only and require human review.",
                "provider": provider.name,
                "recommendations": [
                    {
                        "id": str(r.id),
                        "kind": r.kind,
                        "output": r.output,
                        "confidence": r.confidence,
                    }
                    for r in recommendations
                ],
            }
        )


class AIDecisionView(APIView):
    """POST /api/v1/ai/recommendations/<id>/decide/ — accept/edit/reject."""

    permission_classes = [permissions.IsAuthenticated, IsAuthority]

    def post(self, request, recommendation_id):
        recommendation = AIRecommendation.objects.filter(pk=recommendation_id).first()
        if recommendation is None:
            return Response({"detail": "Recommendation not found."}, status=404)
        decision = request.data.get("decision")
        if decision not in ("accepted", "edited", "rejected"):
            return Response({"detail": "decision must be accepted|edited|rejected."}, status=400)
        recommendation.decision = decision
        recommendation.decided_by = request.user
        recommendation.decided_at = timezone.now()
        recommendation.save(update_fields=["decision", "decided_by", "decided_at"])
        log_action(
            actor=request.user,
            action="ai.decision",
            obj=recommendation,
            changes={
                "decision": decision,
                "kind": recommendation.kind,
                "confidence": recommendation.confidence,
            },
            request=request,
        )
        return Response({"detail": f"Recommendation {decision}.", "id": str(recommendation.id)})


class AIDuplicateCheckView(APIView):
    """POST /api/v1/ai/duplicates/ — AI-assisted duplicate similarity."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "ai"

    def post(self, request):
        provider = get_provider()
        result = provider.check_duplicates(
            request.data.get("title", ""), request.data.get("description", ""), []
        )
        return Response(
            {
                "disclaimer": "AI suggestions are advisory only.",
                "provider": provider.name,
                "result": result,
            }
        )
