# Copyright (c) 2026, Project K
# License: MIT

import frappe
from frappe.utils.nestedset import NestedSet


class Tenant(NestedSet):
	nsm_parent_field = "parent_tenant"

	def validate(self):
		if self.tenant_type == "Anchor" and not self.parent_tenant:
			frappe.throw("An Anchor tenant must have a Cluster set as its Parent Tenant.")
		if self.tenant_type == "Cluster":
			self.is_group = 1
