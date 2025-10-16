"""
Constants and Configuration Module

This module defines global constants and configuration used across the production
monitoring service. It includes timeout values, compliance whitelists, and
allowed configuration change patterns for audit trail monitoring.

Constants:
    - REQUESTS_TIMEOUT_SECONDS: Timeout for external HTTP requests (300s)
    - QUERY_TIMEOUT_SECONDS: Timeout for Salesforce SOQL queries (30s)
    - ALLOWED_SECTIONS_ACTIONS: Whitelist of legitimate SetupAuditTrail actions by section
    - EXCLUDE_USERS: List of admin/integration users excluded from compliance monitoring

Compliance Configuration:
    The ALLOWED_SECTIONS_ACTIONS dictionary defines legitimate actions per Setup section
    to distinguish between normal administrative activities and potentially risky changes.
    
    The EXCLUDE_USERS list contains service accounts and administrators whose actions
    are trusted and should not trigger compliance alerts.
"""
REQUESTS_TIMEOUT_SECONDS = 300
QUERY_TIMEOUT_SECONDS = 30
ALLOWED_SECTIONS_ACTIONS = {
    "": ["createScratchOrg", "changedsenderemail", "deleteScratchOrg", "loginasgrantedtopartnerbt"],
    "Certificate and Key Management": ["insertCertificate"],
    "Custom App Licenses": ["addeduserpackagelicense", "granteduserpackagelicense"],
    "Customer Portal": ["createdcustomersuccessuser"],
    "Currency": ["updateddatedexchrate"],
    "Data Management": ["queueMembership"],
    "Email Administration": ["dkimRotationSuccessful", "dkimRotationPreparationSuccessful"],
    "Holidays": ["holiday_insert"],
    "Inbox mobile and legacy desktop apps": ["enableSIQUserNonEAC"],
    "Groups": ["groupMembership"],
    "Manage Territories": ["tm2_userAddedToTerritory", "tm2_userRemovedFromTerritory"],
    "Manage Users": [
        "activateduser", "createduser", "changedcommunitynickname",
        "changedemail", "changedfederationid", "changedinteractionuseroffon",
        "changedinteractionuseronoff", "changedmarketinguseroffon",
        "changedmarketinguseronoff", "changedManager", "changedprofileforuser",
        "changedprofileforusercusttostd", "changedprofileforuserstdtocust",
        "changedroleforusertonone", "changedroleforuser", "changedroleforuserfromnone",
        "changedpassword", "changedUserEmailVerifiedStatusUnverified",
        "changedUserEmailVerifiedStatusVerified", "changedUserPhoneNumber",
        "changedUserPhoneVerifiedStatusUnverified", "deactivateduser",
        "deleteAuthenticatorPairing", "deleteTwoFactorInfo2", "deleteTwoFactorTempCode",
        "frozeuser", "insertAuthenticatorPairing", "insertTwoFactorInfo2",
        "insertTwoFactorTempCode", "lightningloginenroll", "PermSetAssign",
        "PermSetGroupAssign", "PermSetGroupUnassign", "PermSetLicenseAssign",
        "PermSetUnassign", "PermSetLicenseUnassign", "registeredUserPhoneNumber",
        "resetpassword", "suOrgAdminLogin", "suOrgAdminLogout", "unfrozeuser",
        "useremailchangesent"
    ],
    "Mobile Administration": ["assigneduserstomobileconfig"]
}
EXCLUDE_USERS = ['Salesforce Admin User', 'GitlabIntegration Prod', 'Rajnandini Chavan',
                 'MindMatrix Integration User', 'Okta Integration User',
                 'Matthew Forsyth', 'Matt Carvin', 'Deep Suthar']
