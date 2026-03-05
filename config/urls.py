from django.contrib import admin
from django.urls import path, include
from apps.accounts.views import ClientViewSet, PlanViewSet, OrganizationSubscriptionViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Auth — JWT
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Apps
    path('api/', include('apps.accounts.urls')),
    path('api/', include('apps.quotas.urls')),
    path('api/', include('apps.hypervisors.urls')),
    path('api/', include('apps.virtual_machines.urls')),

    # OpenAPI docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),


    path('api/accounts/clients/', ClientViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('api/accounts/plans/', PlanViewSet.as_view({'get': 'list'})),
    path('api/accounts/subscription/', OrganizationSubscriptionViewSet.as_view({'get': 'retrieve', 'patch': 'update'})),
    path('api/accounts/', include('apps.accounts.urls')),

    path('api/projects/', include('apps.projects.urls')),

]
