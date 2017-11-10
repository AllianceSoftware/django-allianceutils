from django.apps import AppConfig

from allianceutils.util.autodump import AutodumpAppConfigMixin
from allianceutils.util.autodump import AutodumpModelFormats

__all__ = [
    'AutodumpAppConfigMixin',
    'DjangoSiteConfig',
]


class AllianceUtilsAppConfig(AutodumpAppConfigMixin, AppConfig):
    name = 'allianceutils'
    verbose_name = "Alliance Django Utils"

    def get_autodump_labels(self):
        return self.autodump_labels_merge(
            {
                'ignore': AutodumpModelFormats([
                    'admin.LogEntry',
                    'auth.Permission',
                    'contenttypes.ContentType',
                    'sessions.Session',
                ]),
            },
            super().get_autodump_labels()
        )
