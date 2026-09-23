from rest_framework.views import APIView
from rest_framework.response import Response

class CategoryListView(APIView):
    CATEGORIES = [
        {"key": "qurilish", "label": "Qurilish", "icon": "🧱", "accent": "#4E97C4"},
        {"key": "elektrika", "label": "Elektrika", "icon": "🔌", "accent": "#E8B23B"},
        {"key": "santexnika", "label": "Santexnika", "icon": "🚰", "accent": "#3FB6AE"},
        {"key": "avto", "label": "Avto", "icon": "🚗", "accent": "#C9564B"},
    ]
    def get(self, request):
        return Response(self.CATEGORIES)
