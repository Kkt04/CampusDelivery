export type Language = "en" | "hi";

export interface TranslationDictionary {
  // Brand & Eyebrow
  appTitle: string;
  brandSubtitle: string;
  eyebrow: string;

  // Navigation
  navOverview: string;
  navMyPackages: string;
  navReturnParcel: string;
  navPickupHistory: string;
  navNotifications: string;
  navGateDashboard: string;
  navRegisterPackage: string;
  navIncomingPackages: string;
  navPickupHandover: string;
  navIncidents: string;
  navOpsOverview: string;
  navPackages: string;
  navNeedsAttention: string;
  navStorage: string;
  navUsers: string;
  navAuditLog: string;
  navSignOut: string;
  navMenu: string;
  navClose: string;

  // Language Toggle labels
  langToggleLabel: string; // "English → हिंदी" when en, "हिंदी → English" when hi

  // Landing Page
  landingHeadingLine1: string;
  landingHeadingLine2: string;
  landingDescription: string;
  landingSignInBtn: string;
  landingCreateAccountBtn: string;
  landingCustodyLogged: string;
  landingArrivalAlerts: string;
  landingOtpHandover: string;
  landingTrustCustody: string;
  landingTrustAlerts: string;
  landingTrustHandover: string;
  landingFooter: string;

  // Authentication & Sign In
  authSignInTitle: string;
  authSignInSubtitle: string;
  authIdentifierLabel: string;
  authIdentifierPlaceholder: string;
  authPasswordLabel: string;
  authShowPassword: string;
  authHidePassword: string;
  authForgotPassword: string;
  authSignInBtn: string;
  authNewHere: string;
  authCreateAccountLink: string;
  authLocalTestAccounts: string;
  authClickToAutofill: string;
  authLearner: string;
  authSecurity: string;
  authAdmin: string;
  authHubFooter: string;
  signInFailed: string;

  // Forgot Password Modal
  resetPasswordTitle: string;
  resetPasswordSubtitle: string;
  resetNewPasswordLabel: string;
  resetNewPasswordPlaceholder: string;
  resetConfirmPasswordLabel: string;
  resetConfirmPasswordPlaceholder: string;
  resetCancelBtn: string;
  resetSubmitBtn: string;
  resetMinLength: string;
  resetPasswordMismatch: string;
  resetSuccess: string;
  resetFailed: string;

  // Sign Up Page
  signupTitle: string;
  signupSubtitle: string;
  signupFullNameLabel: string;
  signupFullNamePlaceholder: string;
  signupIdLabel: string;
  signupIdPlaceholder: string;
  signupIdHint: string;
  signupEmailLabel: string;
  signupEmailPlaceholder: string;
  signupPhoneLabel: string;
  signupPhonePlaceholder: string;
  signupPasswordLabel: string;
  signupPasswordHint: string;
  signupConfirmPasswordLabel: string;
  signupSubmitBtn: string;
  signupAlreadyHaveAccount: string;
  signupSignInLink: string;

  // Common UI
  loading: string;
  tryAgain: string;
  previous: string;
  next: string;
  of: string;
  noData: string;
  search: string;
  filter: string;
  cancel: string;
  submit: string;
  save: string;
  back: string;
  select: string;
  change: string;
  overdue: string;
  devMode: string;
  confirm: string;
  details: string;

  // Roles
  roleLearner: string;
  roleSecurity: string;
  roleAdmin: string;

  // Statuses
  statusReceived: string;
  statusReceivedLearner: string;
  statusVerified: string;
  statusVerifiedLearner: string;
  statusStored: string;
  statusStoredLearner: string;
  statusReadyForPickup: string;
  statusReadyForPickupLearner: string;
  statusPickupRequested: string;
  statusPickupRequestedLearner: string;
  statusCollected: string;
  statusCollectedLearner: string;
  statusUnidentified: string;
  statusUnidentifiedLearner: string;
  statusDamaged: string;
  statusDamagedLearner: string;
  statusUnderInvestigation: string;
  statusUnderInvestigationLearner: string;
  statusReturnRequested: string;
  statusReturnRequestedLearner: string;
  statusReturned: string;
  statusReturnedLearner: string;
  statusLost: string;
  statusLostLearner: string;

  // Dashboard & Content
  readyToCollectTitle: string;
  pickupHistoryTitle: string;
  pickupHistorySubtitle: string;
  viewAll: string;
  viewPastPickups: string;
  initiateParcelReturn: string;
  activeReturnRequests: string;
  noParcelsReady: string;
  gateDashboardTitle: string;
  gateDashboardSubtitle: string;
  opsOverviewTitle: string;
  opsOverviewSubtitle: string;
  statReceivedToday: string;
  statCollectedToday: string;
  statInCustody: string;
  statAwaitingStorage: string;
  statUnidentified: string;
  statHeldDamaged: string;
  queueWaitingShelf: string;
  queueWaitingShelfEmpty: string;
  queueNeedsReview: string;
  queueNeedsReviewEmpty: string;
  queueStoredNotReady: string;
  queueStoredNotReadyEmpty: string;

  // Package Table
  thPackage: string;
  thRecipient: string;
  thCourier: string;
  thArrived: string;
  thShelf: string;
  thStatus: string;
  noTrackingId: string;
  unknownRecipientText: string;

  // Registration
  regPageTitle: string;
  regPageSubtitle: string;
  regSuccessTitle: string;
  regCourierLabel: string;
  regTrackingLabel: string;
  regTrackingHint: string;
  regArrivedAtLabel: string;
  regSizeLabel: string;
  regSizeSmall: string;
  regSizeMedium: string;
  regSizeLarge: string;
  regShipmentCard: string;
  regRecipientCard: string;
  regStorageCard: string;
  regLearnerLabel: string;
  regUnknownCheckbox: string;
  regUnknownHintLabel: string;
  regUnknownHintPlaceholder: string;
  regUnknownHintHelp: string;
  regRackLabel: string;
  regRackPlaceholder: string;
  regRackHint: string;
  regSubmitBtn: string;
  regStoredAtShelf: string;
  regReadyNotification: string;
  regAnotherBtn: string;
  regAssignStorageBtn: string;

  pickupVerifyTitle: string;
  pickupVerifySubtitle: string;
  pickupPkgCodeLabel: string;
  pickupPkgCodeHint: string;
  pickupCodeLabel: string;
  pickupCodePlaceholder: string;
  pickupVerifyBtn: string;
  pickupCompleteBtn: string;
  pickupSuccessBanner: string;
  pickupHandedOver: string;
  pickupStudentIdLabel: string;
  pickupStudentIdPlaceholder: string;
  pickupPackageFound: string;
  pickupShelfNotice: string;
  pickupNextBtn: string;
  pickupValidCardTitle: string;
  pickupFetchNotice: string;

  // Package Detail
  pkgDetailTitle: string;
  progressTitle: string;
  pkgShipmentInfo: string;
  pkgCollectCard: string;
  pkgCollectInstructions: string;
  pkgGetCodeBtn: string;
  pkgNewCodeBtn: string;
  pkgCollectedNotice: string;
  pkgPendingNotice: string;
  pkgReturnRequestedNotice: string;
  pkgReportProblem: string;
  pkgReportDescLabel: string;
  pkgReportDescPlaceholder: string;
  pkgReportBtn: string;
  pkgReportSuccess: string;
  pkgHistoryCard: string;
  pkgActionsCard: string;
  pkgAssignStorageTitle: string;
  returnToCourier: string;
  requestReturnBtn: string;
  identifyRecipientTitle: string;
  identifyRecipientHelp: string;
  setRecipientBtn: string;
  movePackage: string;
  backToPackages: string;
  reportIncidentForPkg: string;

  // My Packages (Learner)
  myPackagesTitle: string;
  myPackagesSubtitle: string;
  tabReady: string;
  tabIncoming: string;
  tabCollected: string;
  tabAll: string;
  noPackagesInTab: string;

  // Pickup Code
  pickupCodePageTitle: string;
  pickupCodePageSubtitle: string;
  pickupCodeInstructions: string;
  pickupCodeExpires: string;
  pickupCodeGateReminder: string;
  pickupCodeBack: string;
  codeExpiredTitle: string;
  codeExpiredDesc: string;
  getMyCode: string;
  codeValidFor: string;
  codeNoticeOnce: string;
  codeGatePrompt: string;

  // Return Parcel
  returnPageTitle: string;
  returnPageSubtitle: string;
  returnReasonLabel: string;
  returnReasonPlaceholder: string;
  returnSubmitBtn: string;
  returnSuccessNotice: string;

  // Notifications
  notifTitle: string;
  notifSubtitle: string;
  notifMarkAllRead: string;
  notifEmpty: string;

  // Incident Reporting & Reviews
  incidentsTitle: string;
  incidentsSubtitle: string;
  incidentsSecurityDesc: string;
  incidentsOpsDesc: string;
  reportIncidentCard: string;
  recentIncidentsCard: string;
  incidentTypeDamage: string;
  incidentTypeUnidentified: string;
  incidentTypeMissing: string;
  incidentTypeOperational: string;
  filterOpen: string;
  filterResolved: string;
  filterAll: string;
  noOpenIncidents: string;
  resolutionNoteLabel: string;
  resolutionPlaceholder: string;
  markResolvedBtn: string;
  resolveBtn: string;
  reportIncidentBtn: string;

  // Packages List
  incomingPackagesTitle: string;
  incomingPackagesDesc: string;
  allPackagesTitle: string;
  allPackagesDesc: string;
  searchPlaceholder: string;
  filterStatus: string;
  filterAllInCustody: string;
  filterAnyStatus: string;
  filterArrivedFrom: string;
  filterArrivedTo: string;
  filterOverdueOnly: string;
  noPackagesMatch: string;
  noPackagesMatchHelp: string;

  // Exceptions Page
  exceptionsTitle: string;
  exceptionsDesc: string;
  tabOverdue: string;
  tabUnidentified: string;
  tabDamaged: string;
  tabInvestigation: string;
  tabReturns: string;
  emptyOverdue: string;
  emptyUnidentified: string;
  emptyDamaged: string;
  emptyInvestigation: string;
  emptyReturns: string;

  // Storage Management
  storageTitle: string;
  storageDesc: string;
  locationsCard: string;
  addLocationCard: string;
  thLocation: string;
  thHoldsUpTo: string;
  thInUse: string;
  thCapacity: string;
  locationCodeLabel: string;
  locationCodeHint: string;
  locationDescLabel: string;
  locationCapLabel: string;
  locationLargestSizeLabel: string;
  addLocationBtn: string;
  active: string;
  closed: string;
  deactivate: string;
  reactivate: string;

  // Users Management
  usersTitle: string;
  usersDesc: string;
  accountsCard: string;
  thName: string;
  thId: string;
  thRole: string;
  thSince: string;
  allRoles: string;
  addUserCard: string;

  // Audit Log
  auditTitle: string;
  auditDesc: string;
  thWhen: string;
  thWho: string;
  thAction: string;
  thTarget: string;
  thDetails: string;
  filterAction: string;
  filterPackageId: string;
  filterFrom: string;
  filterTo: string;
  allActions: string;
  noAuditMatch: string;

  // Learner Picker & Lifecycle Track
  learnerSearchPlaceholder: string;
  searching: string;
  noMatchingLearner: string;
  offPathMessage: string;

  // Status Pages
  err403Title: string;
  err403Msg: string;
  err404Title: string;
  err404Msg: string;
  goToDashboard: string;
}
