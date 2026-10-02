from rest_framework.routers import DefaultRouter

from .views import LeadViewSet

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("leads", LeadViewSet, basename="lead")

urlpatterns = router.urls
