from __future__ import annotations

from typing import Collection
from typing import Dict
from typing import List
from typing import Protocol
from typing import TYPE_CHECKING

from django.db.models import Field as ModelField
from django.db.models.options import Options
from rest_framework.fields import Field
from rest_framework.serializers import ModelSerializer

if TYPE_CHECKING:
    # ModelSerializer.Meta is only available in DRF stubs
    class DRFSerializerProtocol(Protocol):
        Meta: ModelSerializer.Meta
        fields: Dict[str, Field]

        # this is provided by SerializerOptInFieldsMixin
        def get_pinned_fields(self: DRFSerializerProtocol) -> Collection[str]:
            ...

else:
    class DRFSerializerProtocol:
        pass


class SerializerOptInFieldsMixin:
    """
    Regulates fields exposed by default & as requested based on query parameters or context.

    Pass 'include_fields' / 'opt_in_fields' thru query params or context to use.
    multiple fields can either be separated by comma eg,
    /?include_fields=first_name,email&opt_in_fields=gait_recognition_prediction
    or passed in the traditional list fashion eg,
    /?include_fields=first_name&include_fields=email&opt_in_fields=gait_recognition_prediction
    or mixed eg,
    /?include_fields=first_name,email&include_fields=boo

    1. By default, all "fields" defined in serializer, minus those listed in "opt_in_fields" would be returned.
    2. If "include_fields" is supplied, only fields requested this way would be returned.
    3. If "opt_in_fields" is supplied, fields requested this way PLUS fields from #1 or #2 would be returned.

    Pinned fields are always returned. (currently pk only if pk exists)
    """

    def get_pinned_fields(self: DRFSerializerProtocol) -> Collection[str]:
        """
        Get by-default pinned fields. Pinned fields are fields always returned regardless of include_fields inclusions.
        Override on serializer to customize.

        Currently, the only pinned field is pk of model (with ModelSerializer).

        :return: [] - a list of pinned fields.
        """

        try:
            model = self.Meta.model
            meta: Options = model._meta  # type:ignore[attr-defined]  # _meta is not included in stubs
            assert meta.pk is not None
            pk: ModelField = meta.pk
            return [pk.name]
        except AttributeError:
            pass
        return []

    def __init__(self: DRFSerializerProtocol, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not hasattr(self, "context"):
            # serializer invoked without context - inspection?
            return

        pinned_fields = self.get_pinned_fields()

        fields_to_exclude = getattr(self.Meta, "opt_in_only_fields", [])

        fields_to_include = (
            (
                "request" in self.context
                and "include_fields" in self.context["request"].query_params
                and self.context["request"].query_params["include_fields"]
            )
            or ("include_fields" in self.context and self.context["include_fields"])
            or set(self.Meta.fields).difference(set(fields_to_exclude))
        )

        if isinstance(fields_to_include, str):
            fields_to_include = [fields_to_include]

        fields_to_include_list: List[str] = []
        for f in fields_to_include:
            if f.find(",") != -1:
                fields_to_include_list += f.split(",")
            else:
                fields_to_include_list.append(f)

        opt_in_fields_to_include = (
            (
                "request" in self.context
                and "opt_in_fields" in self.context["request"].query_params
                and self.context["request"].query_params["opt_in_fields"]
            )
            or ("opt_in_fields" in self.context and self.context["opt_in_fields"])
            or []
        )

        for f in list(self.fields.keys()):
            if (
                f not in pinned_fields
                and f not in fields_to_include_list
                and f not in opt_in_fields_to_include
            ):
                del self.fields[f]

        return
