from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (CustomTokenObtainPairView,
                    RegisterView, UserViewSet)
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path("login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('register/', RegisterView.as_view(), name='register_user'),
]

urlpatterns += router.urls
