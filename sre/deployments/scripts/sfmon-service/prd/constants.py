""" Constants."""
REQUESTS_TIMEOUT_SECONDS = 300
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
PRD_ALIAS = 'prd'
