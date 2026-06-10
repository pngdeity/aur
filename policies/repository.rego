package main

import rego.v1

# ─────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────

coalesce_checksums(pkg) := c if {
	pkg.sha256sums != null
	c = pkg.sha256sums
} else := c if {
	pkg.sha512sums != null
	c = pkg.sha512sums
} else := c if {
	pkg.sha224sums != null
	c = pkg.sha224sums
} else := c if {
	pkg.sha384sums != null
	c = pkg.sha384sums
} else := c if {
	pkg.b2sums != null
	c = pkg.b2sums
} else := [] if {
	c = []
}

is_vcs_url(url) if {
	startswith(url, "git+")
}

is_vcs_url(url) if {
	startswith(url, "svn+")
}

is_vcs_url(url) if {
	startswith(url, "hg+")
}

is_vcs_url(url) if {
	startswith(url, "bzr+")
}

is_pinned_source(url) if {
	contains(url, "#tag=")
}

is_pinned_source(url) if {
	contains(url, "#commit=")
}

is_empty_or_null(v) if {
	v == null
}

is_empty_or_null(v) if {
	v == ""
}

is_empty_or_null(v) if {
	v == 0
}

is_empty_or_null(v) if {
	count(v) == 0
}

has_field(obj, field) if {
	object.get(obj, field, "__missing_sentinel__") != "__missing_sentinel__"
}

conflict_in_provides(pkg, target) if {
	pkg.provides[_] == target
}

conflict_in_provides(pkg, target) if {
	some provide
	provide = pkg.provides[_]
	startswith(provide, concat("", [target, "="]))
}

conflict_in_provides(pkg, target) if {
	some provide
	provide = pkg.provides[_]
	startswith(provide, concat("", [target, "<"]))
}

conflict_in_provides(pkg, target) if {
	some provide
	provide = pkg.provides[_]
	startswith(provide, concat("", [target, ">"]))
}

# ─────────────────────────────────────────────────────────────────────
# Exception helper: checks if a package has a registered exception
# for a given rule. Exception data is merged into input.exceptions
# by validate-pkgbuilds-pkl.sh from per-package policy_exceptions.yaml.
# ─────────────────────────────────────────────────────────────────────
has_exception(pkg, rule) if {
	not input.exceptions == null
	input.exceptions[pkg.pkgname][rule]
}

# ─────────────────────────────────────────────────────────────────────
# Rule 1: enforce_https (ERROR)
# Source URL protocols must be https:// or git+https://
# FTP sources are valid per PKGBUILD(5)
# ─────────────────────────────────────────────────────────────────────
_all_source_arrays := {"source", "source_x86_64", "source_aarch64"}

deny_enforce_https contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "enforce_https")
	name := _all_source_arrays[_]
	src := object.get(pkg, name, [])[_]
	contains(src.url, "://")
	not startswith(src.url, "https://")
	not startswith(src.url, "git+https://")
	not startswith(src.url, "ftp://")
	msg := sprintf(
		"%s: source URL '%s' must use HTTPS (enforce_https rule)",
		[pkg.pkgname, src.url],
	)
}

deny_enforce_https contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "enforce_https")
	startswith(pkg.url, "http://")
	msg := sprintf(
		"%s: url field '%s' must use HTTPS (enforce_https rule)",
		[pkg.pkgname, pkg.url],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 2: privilege_escalation (WARN)
# No use of `sudo` in lifecycle functions — doas is the approved
# privilege escalation mechanism.
# ─────────────────────────────────────────────────────────────────────
warn_privilege_escalation contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "privilege_escalation")

	func_fields := [pkg.prepare, pkg.build, pkg.check, pkg.packageFunc, pkg.pkgverFunc]
	field_names := ["prepare", "build", "check", "package", "pkgver_func"]

	func := func_fields[i]
	func != null
	regex.match(`\bsudo\b`, func)

	msg := sprintf(
		"%s: 'sudo' string found in %s() — use doas instead (privilege_escalation rule)",
		[pkg.pkgname, field_names[i]],
	)
}

warn_privilege_escalation contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "privilege_escalation")
	pkg.install != null
	msg := sprintf(
		"%s: has .install scriptlet '%s' — manually verify no sudo usage (privilege_escalation rule)",
		[pkg.pkgname, pkg.install],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 3: architecture_mismatch (WARN)
# If arch is ["any"], the package should not declare architecture-
# specific dependencies or build flags.
# ─────────────────────────────────────────────────────────────────────
warn_architecture_mismatch contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "architecture_mismatch")
	pkg.arch == ["any"]

	arch_specific_deps := {"glibc", "lib32-glibc", "gcc-libs"}
	dep := pkg.depends[_]
	dep in arch_specific_deps

	msg := sprintf(
		"%s: arch='any' but depends on arch-specific package '%s' (architecture_mismatch rule)",
		[pkg.pkgname, dep],
	)
}

warn_architecture_mismatch contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "architecture_mismatch")
	pkg.arch == ["any"]

	arch_specific_deps := {"glibc", "lib32-glibc", "gcc-libs"}
	dep := pkg.makedepends[_]
	dep in arch_specific_deps

	msg := sprintf(
		"%s: arch='any' but makedepends on arch-specific package '%s' (architecture_mismatch rule)",
		[pkg.pkgname, dep],
	)
}

warn_architecture_mismatch contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "architecture_mismatch")
	pkg.arch == ["any"]

	funcs := [pkg.prepare, pkg.build, pkg.check, pkg.packageFunc]
	func_names := ["prepare", "build", "check", "package"]
	func := funcs[i]
	func != null
	contains(func, "CARCH")

	msg := sprintf(
		"%s: arch='any' but %s() references CARCH (architecture_mismatch rule)",
		[pkg.pkgname, func_names[i]],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 4: no_unprovided_conflicts (ERROR)
# Every entry in conflicts and replaces must have a matching entry
# in provides.
# ─────────────────────────────────────────────────────────────────────
deny_no_unprovided_conflicts contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "no_unprovided_conflicts")
	conflict := pkg.conflicts[_]
	not conflict_in_provides(pkg, conflict)

	msg := sprintf(
		"%s: conflicts '%s' has no matching entry in provides (no_unprovided_conflicts rule)",
		[pkg.pkgname, conflict],
	)
}

deny_no_unprovided_conflicts contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "no_unprovided_conflicts")
	replace := pkg.replaces[_]
	not conflict_in_provides(pkg, replace)

	msg := sprintf(
		"%s: replaces '%s' has no matching entry in provides (no_unprovided_conflicts rule)",
		[pkg.pkgname, replace],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 5: no_self_reference (ERROR)
# A package must not list its own pkgname in provides or conflicts.
# ─────────────────────────────────────────────────────────────────────
deny_no_self_reference contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "no_self_reference")
	pkg.provides[_] == pkg.pkgname
	msg := sprintf(
		"%s: self-reference — provides contains own pkgname '%s' (no_self_reference rule)",
		[pkg.pkgname, pkg.pkgname],
	)
}

deny_no_self_reference contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "no_self_reference")
	pkg.conflicts[_] == pkg.pkgname
	msg := sprintf(
		"%s: self-reference — conflicts contains own pkgname '%s' (no_self_reference rule)",
		[pkg.pkgname, pkg.pkgname],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 6: deploy_aur_subarch_mutex (moved to Pkl constraint)
# Enforced natively by schemas/arch_pkg.pkl — the Rego version is retired.
# Removed 2026-05-23: Pkl's local fixed constraint sees hidden fields
# that OPA cannot access via JSON manifest.
# ─────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────
# Rule 7: pkgdesc_consistency (ERROR)
# All packages sharing the same _pkgname must have identical pkgdesc.
# ─────────────────────────────────────────────────────────────────────
deny_pkgdesc_consistency contains msg if {
	some k1, k2
	pkg1 := input.packages[k1]
	pkg2 := input.packages[k2]
	not has_exception(pkg1, "pkgdesc_consistency")
	not has_exception(pkg2, "pkgdesc_consistency")
	k1 < k2
	pkg1._pkgname == pkg2._pkgname
	pkg1._pkgname != null
	pkg1.pkgdesc != pkg2.pkgdesc

	msg := sprintf(
		"_pkgname '%s': pkgdesc mismatch — '%s' (%s) vs '%s' (%s) (pkgdesc_consistency rule)",
		[pkg1._pkgname, pkg1.pkgdesc, pkg1.pkgname, pkg2.pkgdesc, pkg2.pkgname],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 8: valid_architectures (ERROR)
# Arch array values must be from the known set (matching KnownArchitecture in Pkl schema).
# ─────────────────────────────────────────────────────────────────────
deny_valid_architectures contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "valid_architectures")
	valid_arches := {"x86_64", "aarch64", "i686", "armv7h", "arm", "any"}

	arch := pkg.arch[_]
	not valid_arches[arch]

	msg := sprintf(
		"%s: unknown architecture '%s' — must be one of: x86_64, aarch64, i686, armv7h, arm, any (valid_architectures rule)",
		[pkg.pkgname, arch],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 9: required_fields (ERROR)
# pkgname, pkgver, pkgrel, pkgdesc, arch, url, license must be
# present and non-empty.
# ─────────────────────────────────────────────────────────────────────
deny_required_fields contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "required_fields")
	required := [
		{"name": "pkgname", "value": pkg.pkgname},
		{"name": "pkgver", "value": pkg.pkgver},
		{"name": "pkgrel", "value": pkg.pkgrel},
		{"name": "pkgdesc", "value": pkg.pkgdesc},
		{"name": "arch", "value": pkg.arch},
		{"name": "url", "value": pkg.url},
		{"name": "license", "value": pkg.license},
	]

	field := required[i]
	is_empty_or_null(field.value)

	msg := sprintf(
		"%s: required field '%s' is missing or empty (required_fields rule)",
		[pkg.pkgname, field.name],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 10: source_integrity (ERROR)
# If source[] (or arch-specific variant) is present, a matching
# checksum array must be present and its length must match.
# ─────────────────────────────────────────────────────────────────────

# Generic source ↔ checksum
deny_source_integrity contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "source_integrity")
	count(pkg.source) > 0
	not has_field(pkg, "sha256sums")
	not has_field(pkg, "sha512sums")
	not has_field(pkg, "sha224sums")
	not has_field(pkg, "sha384sums")
	not has_field(pkg, "b2sums")

	msg := sprintf(
		"%s: source[] has %d entries but no checksum array present (source_integrity rule)",
		[pkg.pkgname, count(pkg.source)],
	)
}

deny_source_integrity contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "source_integrity")
	checksums := coalesce_checksums(pkg)
	count(pkg.source) != count(checksums)

	msg := sprintf(
		"%s: source[] has %d entries but checksums has %d entries (source_integrity rule)",
		[pkg.pkgname, count(pkg.source), count(checksums)],
	)
}

# Arch-specific source_x86_64 ↔ sha512sums_x86_64
deny_source_integrity contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "source_integrity")
	count(pkg.source_x86_64) > 0
	not has_field(pkg, "sha512sums_x86_64")

	msg := sprintf(
		"%s: source_x86_64[] has %d entries but no sha512sums_x86_64 present (source_integrity rule)",
		[pkg.pkgname, count(pkg.source_x86_64)],
	)
}

deny_source_integrity contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "source_integrity")
	count(pkg.source_x86_64) != count(pkg.sha512sums_x86_64)

	msg := sprintf(
		"%s: source_x86_64[] has %d entries but sha512sums_x86_64 has %d entries (source_integrity rule)",
		[pkg.pkgname, count(pkg.source_x86_64), count(pkg.sha512sums_x86_64)],
	)
}

# Arch-specific source_aarch64 ↔ sha512sums_aarch64
deny_source_integrity contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "source_integrity")
	count(pkg.source_aarch64) > 0
	not has_field(pkg, "sha512sums_aarch64")

	msg := sprintf(
		"%s: source_aarch64[] has %d entries but no sha512sums_aarch64 present (source_integrity rule)",
		[pkg.pkgname, count(pkg.source_aarch64)],
	)
}

deny_source_integrity contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "source_integrity")
	count(pkg.source_aarch64) != count(pkg.sha512sums_aarch64)

	msg := sprintf(
		"%s: source_aarch64[] has %d entries but sha512sums_aarch64 has %d entries (source_integrity rule)",
		[pkg.pkgname, count(pkg.source_aarch64), count(pkg.sha512sums_aarch64)],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 11: vcs_skip (WARN)
# Non-VCS source entries should not have SKIP checksums.
# ─────────────────────────────────────────────────────────────────────
warn_vcs_skip contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "vcs_skip")
	checksums := coalesce_checksums(pkg)
	src := pkg.source[i]
	checksums[i] == "SKIP"
	not is_vcs_url(src.url)

	msg := sprintf(
		"%s: non-VCS source '%s' has SKIP checksum — should have integrity hash (vcs_skip rule)",
		[pkg.pkgname, src.filename],
	)
}

warn_vcs_skip contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "vcs_skip")
	checksums := coalesce_checksums(pkg)
	src := pkg.source[i]
	checksums[i] == "SKIP"
	is_pinned_source(src.url)

	msg := sprintf(
		"%s: pinned source '%s' has SKIP checksum — should have integrity hash (vcs_skip rule)",
		[pkg.pkgname, src.filename],
	)
}

warn_vcs_skip contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "vcs_skip")
	src := pkg.source_x86_64[i]
	pkg.sha512sums_x86_64[i] == "SKIP"
	not is_vcs_url(src.url)

	msg := sprintf(
		"%s: non-VCS source_x86_64 '%s' has SKIP checksum — should have integrity hash (vcs_skip rule)",
		[pkg.pkgname, src.filename],
	)
}

warn_vcs_skip contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "vcs_skip")
	src := pkg.source_aarch64[i]
	pkg.sha512sums_aarch64[i] == "SKIP"
	not is_vcs_url(src.url)

	msg := sprintf(
		"%s: non-VCS source_aarch64 '%s' has SKIP checksum — should have integrity hash (vcs_skip rule)",
		[pkg.pkgname, src.filename],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 12: deny_missing_maintainer (FAIL)
# Every package must declare a maintainer in "Name <email>" format.
# The Pkl schema enforces format — this is a presence safety net.
# ─────────────────────────────────────────────────────────────────────
deny_missing_maintainer contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "missing_maintainer")
	object.get(pkg, "maintainer", null) == null
	msg := sprintf(
		"%s: maintainer is missing (must be 'Name <email>')",
		[pkg.pkgname],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 13: deny_arch_any_arch_specific (ERROR)
# arch=('any') packages must not declare architecture-specific
# source arrays — makepkg will never download them.
# ─────────────────────────────────────────────────────────────────────
deny_arch_any_arch_specific contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "arch_any_arch_specific")
	pkg.arch == ["any"]
	count(pkg.source_x86_64) > 0
	msg := sprintf(
		"%s: arch='any' but source_x86_64[] has %d entries — arch-specific sources will never be downloaded (arch_any_arch_specific rule)",
		[pkg.pkgname, count(pkg.source_x86_64)],
	)
}

deny_arch_any_arch_specific contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "arch_any_arch_specific")
	pkg.arch == ["any"]
	count(pkg.source_aarch64) > 0
	msg := sprintf(
		"%s: arch='any' but source_aarch64[] has %d entries — arch-specific sources will never be downloaded (arch_any_arch_specific rule)",
		[pkg.pkgname, count(pkg.source_aarch64)],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 14: deny_vcs_without_skip (ERROR)
# VCS source URLs (git+, svn+, hg+, bzr+) must have "SKIP" checksums.
# Without SKIP, makepkg will checksum-verify a moving target.
# ─────────────────────────────────────────────────────────────────────
deny_vcs_without_skip contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "vcs_without_skip")
	checksums := coalesce_checksums(pkg)
	src := pkg.source[i]
	is_vcs_url(src.url)
	not is_pinned_source(src.url)
	checksums[i] != "SKIP"

	msg := sprintf(
		"%s: VCS source '%s' must have SKIP checksum (vcs_without_skip rule)",
		[pkg.pkgname, object.get(src, "filename", src.url)],
	)
}

deny_vcs_without_skip contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "vcs_without_skip")
	src := pkg.source_x86_64[i]
	is_vcs_url(src.url)
	not is_pinned_source(src.url)
	pkg.sha512sums_x86_64[i] != "SKIP"

	msg := sprintf(
		"%s: VCS source_x86_64 '%s' must have SKIP checksum (vcs_without_skip rule)",
		[pkg.pkgname, object.get(src, "filename", src.url)],
	)
}

deny_vcs_without_skip contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "vcs_without_skip")
	src := pkg.source_aarch64[i]
	is_vcs_url(src.url)
	not is_pinned_source(src.url)
	pkg.sha512sums_aarch64[i] != "SKIP"

	msg := sprintf(
		"%s: VCS source_aarch64 '%s' must have SKIP checksum (vcs_without_skip rule)",
		[pkg.pkgname, object.get(src, "filename", src.url)],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 15: deny_no_version_constraints (ERROR)
# Version operators (>=, <=, >, <, =) in depends/makedepends/checkdepends
# are non-functional — pacman does not enforce version ranges.
# ─────────────────────────────────────────────────────────────────────
deny_no_version_constraints contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "no_version_constraints")
	dep_lists := [
		{"name": "depends", "entries": object.get(pkg, "depends", [])},
		{"name": "makedepends", "entries": object.get(pkg, "makedepends", [])},
		{"name": "checkdepends", "entries": object.get(pkg, "checkdepends", [])},
	]
	dep := dep_lists[i].entries[j]
	regex.match(`[<>]=`, dep)
	msg := sprintf(
		"%s: %s entry '%s' contains version operator — pacman does not enforce version ranges (no_version_constraints rule)",
		[pkg.pkgname, dep_lists[i].name, dep],
	)
}

deny_no_version_constraints contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "no_version_constraints")
	dep_lists := [
		{"name": "depends", "entries": object.get(pkg, "depends", [])},
		{"name": "makedepends", "entries": object.get(pkg, "makedepends", [])},
		{"name": "checkdepends", "entries": object.get(pkg, "checkdepends", [])},
	]
	dep := dep_lists[i].entries[j]
	regex.match(`\b=\d`, dep)
	msg := sprintf(
		"%s: %s entry '%s' contains version constraint — pacman does not enforce version ranges (no_version_constraints rule)",
		[pkg.pkgname, dep_lists[i].name, dep],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Rule 16: warn_prefer_strong_hash (WARN)
# md5sums without sha256sums, sha512sums, or b2sums is cryptographically
# weak — SHA-256 or stronger is preferred per Arch Wiki guidelines.
# ─────────────────────────────────────────────────────────────────────
warn_prefer_strong_hash contains msg if {
	pkg := input.packages[_]
	not has_exception(pkg, "prefer_strong_hash")
	count(pkg.md5sums) > 0
	not has_field(pkg, "sha256sums")
	not has_field(pkg, "sha512sums")
	not has_field(pkg, "b2sums")
	msg := sprintf(
		"%s: md5sums used but no sha256/sha512/b2sums present — prefer stronger hash (prefer_strong_hash rule)",
		[pkg.pkgname],
	)
}

# ─────────────────────────────────────────────────────────────────────
# Legacy exception rule — inert. Policy exceptions are now wired
# through input.exceptions (merged by validate-pkgbuilds-pkl.py)
# and checked via has_exception() in each rule above.
# Retained for tool compatibility only.
# ─────────────────────────────────────────────────────────────────────
exception contains rules if {
	pkg := input.packages[_]
	not input.exceptions == null
	exc := input.exceptions[pkg.pkgname]
	rules := [exc[_]]
}
