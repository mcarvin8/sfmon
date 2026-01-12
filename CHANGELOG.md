# Changelog

## [3.1.0](https://github.com/mcarvin8/sfmon/compare/v3.0.0...v3.1.0) (2026-01-12)


### Features

* restructure codebase into packages and add audit compliance functions ([#7](https://github.com/mcarvin8/sfmon/issues/7)) ([b4b54db](https://github.com/mcarvin8/sfmon/commit/b4b54dbd2da629ac0ab9302cdef869258ac976d6))

## [3.0.0](https://github.com/mcarvin8/sfmon/compare/v2.0.2...v3.0.0) (2026-01-09)


### ⚠ BREAKING CHANGES

* Jobs must now be explicitly defined in config.json to run. Previously, all jobs ran by default unless disabled. Now, only jobs listed in the schedules section will execute.

### Features

* add scheduled apex job monitoring, refactor tech debt monitoring functions ([cf3542a](https://github.com/mcarvin8/sfmon/commit/cf3542afc93437eace36e381f5f9c024421f0b14))
* change job scheduling to opt-in configuration model ([9902b51](https://github.com/mcarvin8/sfmon/commit/9902b5198fd9a13359c2ffa54a5803c430a4b55d))

## [2.0.2](https://github.com/mcarvin8/sfmon/compare/v2.0.1...v2.0.2) (2025-12-29)


### Bug Fixes

* use temp file for connection to sf ([5445e07](https://github.com/mcarvin8/sfmon/commit/5445e076dc7deb963584d3fb63a6ee449c83f0f9))

## [2.0.1](https://github.com/mcarvin8/sfmon/compare/v2.0.0...v2.0.1) (2025-12-10)


### Bug Fixes

* address security injection concerns on sf connection commands ([124f633](https://github.com/mcarvin8/sfmon/commit/124f633ede8ef3572c7b4642ebd9090e39db7864))

## [2.0.0](https://github.com/mcarvin8/sfmon/compare/v1.1.0...v2.0.0) (2025-11-25)


### ⚠ BREAKING CHANGES

* Remove support for SCHEDULE_<JOB_ID> and INTEGRATION_USER_NAMES environment variables. All scheduling and user configuration must now be managed through config.json file.

### Features

* remove environment variable support for scheduling and user config ([55b8495](https://github.com/mcarvin8/sfmon/commit/55b8495d0b62622650cf3c256d628269c976e408))

## [1.1.0](https://github.com/mcarvin8/sfmon/compare/v1.0.0...v1.1.0) (2025-11-24)


### Features

* add QUERY_TIMEOUT_SECONDS environment variable ([5f8941d](https://github.com/mcarvin8/sfmon/commit/5f8941d68e36987564ed7c30afa262dd83110556))
* add tech debt monitoring functions ([4795e2a](https://github.com/mcarvin8/sfmon/commit/4795e2af5c4546a4326be0086ab6e5d9378f662f))

## 1.0.0 (2025-11-24)


### Features

* add bulk api and compliance functions ([3631838](https://github.com/mcarvin8/sfmon/commit/36318387e91bb829079ce197da742ae7079c9a23))
* add init grafana dashboard config ([3c13374](https://github.com/mcarvin8/sfmon/commit/3c13374ce90273d42d21c70838e4979d811e8ae5))
* add latest updates ([ea28433](https://github.com/mcarvin8/sfmon/commit/ea2843372f39bc91244e1469c538ed8b929b658f))
* add more function specific files ([6892e17](https://github.com/mcarvin8/sfmon/commit/6892e17838a4d010822f563574393771ff27d408))
* add sample prometheus config with ecs file scraping ([bbb3876](https://github.com/mcarvin8/sfmon/commit/bbb38762eef0772df3f9965c2e5e2e2df67e8d27))
* add schedules ([f7d69d8](https://github.com/mcarvin8/sfmon/commit/f7d69d8a2efe51060567b89c3b9320b86e9037bd))
* add tooling api query function ([4147e95](https://github.com/mcarvin8/sfmon/commit/4147e95daafde652b0af4c9d8d62e92b876ac4c9))
* add validation deploy metrics ([35173ed](https://github.com/mcarvin8/sfmon/commit/35173ed5fc08cbb868589048107268d791b0b2d0))
* backup latest versions ([24c3f44](https://github.com/mcarvin8/sfmon/commit/24c3f44b7428de47c4c9e0af7dc6e16ce60df672))
* expose average page time data ([1356321](https://github.com/mcarvin8/sfmon/commit/13563212932b76ab132cd2b7272cefde404ee6be))
* focus on just 1 org ([ffd77ef](https://github.com/mcarvin8/sfmon/commit/ffd77ef608577d16d5698623a88604f14547b769))
* init commit ([24c5c88](https://github.com/mcarvin8/sfmon/commit/24c5c88967eb15f400610dc47daa038e5ca3b831))
* latest grafana dashboard json ([6e06357](https://github.com/mcarvin8/sfmon/commit/6e063571523973cc7c543c16fa78f256e73a5b94))
* monitor deprecated apex classes ([22847fc](https://github.com/mcarvin8/sfmon/commit/22847fc5779380c4b60e60906d9a4650e4ec3b76))
* pull ecr and iam role into ecs ([f7de6a2](https://github.com/mcarvin8/sfmon/commit/f7de6a235b7611aaad184aaed286e3bbf564a7d1))
* pull sg ([58b4d02](https://github.com/mcarvin8/sfmon/commit/58b4d027c54ddb4a53696fdf1c1fbe4af1aa5e3c))
* push latest updates and redo repo ([8ea7156](https://github.com/mcarvin8/sfmon/commit/8ea71565669d2f6a004372c24d8cbcf07ea2d534))
* re-add infra for prometheus and ecs ([273e685](https://github.com/mcarvin8/sfmon/commit/273e685fa1172be7950d19043dc9fe85c0c8d207))
* readd apex tech debt function ([56c6e95](https://github.com/mcarvin8/sfmon/commit/56c6e95bd7c029c7e71fd967c0510666f9e94ed8))
* remove simple salesforce dependency ([0b7e29a](https://github.com/mcarvin8/sfmon/commit/0b7e29a9c3ced46e5402047bf98ad210643b411d))
* restore simple salesforce and use apscheduler instead of schedule ([1857cee](https://github.com/mcarvin8/sfmon/commit/1857ceebab39c27d73ac6b64e5bbb5ccfcdfc789))
* separate scripts and docker into prd and sbx folders ([87a11a8](https://github.com/mcarvin8/sfmon/commit/87a11a861be169fd05cf15c325737f9548012ace))
* simplify tf structure ([930e640](https://github.com/mcarvin8/sfmon/commit/930e64065fc6061c13c26c1b7f59af512155620c))
* update tech debt functions ([75f8101](https://github.com/mcarvin8/sfmon/commit/75f8101d64188b80073a44d85906f518cb108c65))
* update terraform structure ([3e2d0e2](https://github.com/mcarvin8/sfmon/commit/3e2d0e215ccbdd7b6eb45e4cdd45d11fc0d56a50))
* update to latest dashboard ([c2f1b7d](https://github.com/mcarvin8/sfmon/commit/c2f1b7db94f5ebc6a599050e5032d96ddcd6dd8c))


### Bug Fixes

* add tech debt gauges ([18dbeca](https://github.com/mcarvin8/sfmon/commit/18dbeca52f27891a1479cd0d5715cd85b9af9b21))
* logic on handling apex exceptions ([f521963](https://github.com/mcarvin8/sfmon/commit/f521963a01a6c1d81e5f3ffc7641f25627fa5c6e))
* new scripts path for docker ([62b8ea0](https://github.com/mcarvin8/sfmon/commit/62b8ea0d6b87f8619cb087fd96f48e68bbe57e09))
* remove unused constant ([4588f36](https://github.com/mcarvin8/sfmon/commit/4588f362559d6eaca7f8f307a4364235128b603a))
* remove unused gauge and clear the api limits gauge ([5d24d7d](https://github.com/mcarvin8/sfmon/commit/5d24d7d247821d5850cbade47b6f07ff0d71e400))
* sfmon cluster name ([c0f642a](https://github.com/mcarvin8/sfmon/commit/c0f642a7d79c8cd32145579a059f0bcdc8a094fd))
