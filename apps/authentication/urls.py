from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, CustomTokenObtainPairView, ProfileView, OrgUsersListView, UserInviteView, UserRoleUpdateView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', ProfileView.as_view(), name='auth_me'),
    path('org/users/', OrgUsersListView.as_view(), name='org_users_list'),
    path('org/users/invite/', UserInviteView.as_view(), name='org_users_invite'),
    path('org/users/<int:pk>/role/', UserRoleUpdateView.as_view(), name='org_users_role_update'),
]
