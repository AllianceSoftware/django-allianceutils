from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import traceback

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.handlers.base import BaseHandler
from django.core.signals import got_request_exception
from django.utils import six
from rest_framework.response import Response
from rest_framework.views import APIView


logger = logging.getLogger('django.request')


# Based on django-jsonview https://github.com/jsocol/django-jsonview
# Copyright 2013 James Socol
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
class JSONExceptionAPIView(APIView):

    default_error_message = 'An error occurred.'

    def handle_exception(self, exc):

        # Perform original handling
        try:
            return super(JSONExceptionAPIView, self).handle_exception(exc)

        # If the exception is re-raised, handle it ourselves
        except PermissionDenied as e:
            logger.warning(
                'Forbidden (Permission denied): %s', self.request.path,
                extra={
                    'status_code': 403,
                })
            exc_data = {
                'error': 403,
                'message': six.text_type(e),
            }
            return Response(exc_data, status=403)

        except Exception as e:
            exc_data = {
                'error': 500,
                'message': self.default_error_message,
            }
            if settings.DEBUG:
                exc_data['message'] = six.text_type(e)
                exc_data['traceback'] = traceback.format_exc()

            # Generate the usual 500 error email with stack trace and full
            # debugging information
            logger.error(
                'Internal Server Error: %s', self.request.path,
                exc_info=True,
                extra={
                    'status_code': 500,
                    'request': self.request
                }
            )

            # Here we lie a little bit. Because we swallow the exception,
            # the BaseHandler doesn't get to send this signal. It sets the
            # sender argument to self.__class__, in case the BaseHandler
            # is subclassed.
            got_request_exception.send(sender=BaseHandler, request=self.request)

            return Response(exc_data, status=500)
