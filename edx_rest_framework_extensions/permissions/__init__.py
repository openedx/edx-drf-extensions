# Support backward compatibility of imports prior to creating a permissions directory
from .redirect import LoginRedirectIfUnauthenticated
from .basic import (
  IsSuperuser,
  IsStaff,
  IsUserInUrl
)
