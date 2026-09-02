# Copyright (c) 2026, Project K
# License: MIT

from identity_core.utils.proxy_action import stamp_proxy_action


def before_insert(doc, method=None):
	stamp_proxy_action(doc)


def before_save(doc, method=None):
	stamp_proxy_action(doc)
