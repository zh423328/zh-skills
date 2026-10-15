# uni-app-uts-native-sdk

用 uni-app UTS 插件封装三方原生 SDK（Android / iOS 双端统一 API）的技能。覆盖插件目录规范、原生依赖声明、协议 / 代理实现、权限申请与后台能力，以及把既有原生插件（aar / framework）迁移改造为 UTS 插件的完整方法论。

本 skill 的核心主张：**两端一套 API，业务层不写 `#ifdef APP-PLUS`**。所有坑点均来自真实云打包实测，不是文档推断。

## 适合谁用

- 要把原生 SDK（高德定位 / 地图、推送、支付、相机等）封装成 uni-app 插件，供 JS 层调用的开发者
- 写了 UTS 插件但编译报错、回调不触发，需要排查方法论的人
- 项目里有旧的 `requireNativePlugin` 原生插件（aar / framework），想迁移改造为 UTS 插件
- 封装定位 / 轨迹 / 后台上报类能力，被权限和后台存活问题卡住的团队
- 设计双端一致 API 时不知道 `{ success, fail, complete }`、错误通道、状态查询该怎么定的开发者

## 一句话描述

你说"把这个原生 SDK 封装成 uni-app 插件"，它给你一套经过生产验证的 UTS 插件方法论——目录怎么建、依赖怎么声明、数字类型怎么转、权限怎么递增申请、旧插件怎么迁移，连同 22 条实测踩坑和交付自检清单。

## 触发关键词

```
封装原生 SDK 成 uni-app 插件、UTS 插件对接高德/SDK、
双端统一定位/地图/推送 API、utssdk app-android app-ios 怎么写、
原生插件改 UTS、UTS 迁移、UTS 编译报错、回调不触发、
自定义基座、后台定位封装、requireNativePlugin 迁移
```

## 核心内容速览

| 主题 | 关键结论 |
|---|---|
| **插件目录规范** | `uni_modules/<plugin-id>/utssdk/` 下 `interface.uts`（类型+纯函数，两端共用）+ 分平台 `app-android/index.uts`（编译为 Kotlin）/ `app-ios/index.uts`（编译为 Swift）+ `utssdk/index.uts` 兜底；页面从插件根 import，不要直接 import interface.uts |
| **依赖声明** | Android `config.json` 声明 Maven 依赖 / abis / minSdkVersion；iOS 声明 CocoaPods / frameworks / deploymentTarget；**版本号以 Maven metadata / pod 页为准**，不信文档正文 |
| **数字类型转换（头号坑）** | UTS 的 `number` 在 Android 编译为 `kotlin.Number`，**不会自动转换**：原生 → JS 用 `Number.from()`（绝不能写 `Number(x)`）；JS → 原生用 `toInt()/toLong()/toDouble()/toFloat()`。口诀「进 `Number.from`，出 `toXXX`」 |
| **iOS 语法差异** | 方法标签用 `=` 不用 `:`（`for = AVMediaType.video`）；不支持 trailing closure；协议方法每个参数都要显式 `@argumentLabel`，写错不报错、只是永远不回调 |
| **权限申请** | Android 必须**递增申请**：前台定位 → `POST_NOTIFICATIONS` → `ACCESS_BACKGROUND_LOCATION`，每批独占一次，否则后台定位拿不到且不弹窗不抛异常 |
| **API 设计** | 单次能力三段式 `{ success, fail, complete }`；持续能力 `onXxxChange/offXxxChange/start/stop`；**必须有独立错误通道 `onXxxError`**；区分「失败」与「能力降级」 |
| **权限类插件** | 必须提供「体检 + 导诊」：`checkXxxReady()` 返回 `ready / issue / canRequestPermission / settingsType / message`，按「系统总开关 → 基础权限 → 后台权限 → 省电策略」优先级判定 |
| **后台能力生命周期** | 前台持续能力归**页面**，后台持续能力归 **App / 业务任务**；页面 `onUnmounted` 只解绑 UI 回调不停能力；数据上报与 UI 渲染拆成两个回调 |
| **旧插件迁移** | 契约反编译还原（`javap -c -p` / `nm -gU`）→ 调用点按「插件名+方法名」全项目扫描（三方组件藏在 uni_modules 里）→ manifest 合并注意 FileProvider authority 唯一 |
| **编译运行** | 改 `index.uts` 任何一行 → **必须重做自定义基座**；只改 JS 不用。UTS 原生编译链路依赖 HBuilderX |

## 怎么用这个 skill

这个 skill 是方法论型技能，不提供可复制源码，使用时把 SKILL.md 当规范手册查：

1. **动手前**：先读「目录规范」和「依赖声明」搭好骨架；
2. **写原生代码时**：按「UTS 语法硬要点」逐条核对，尤其 3.1 数字类型转换；
3. **交付前**：走一遍「交付自检」+ 22 条踩坑清单；
4. **迁移旧插件时**：直接翻「五之四」节，按反编译 → 扫描 → 合并的流程走。

## 适用范围判断

- **适用**：uni-app（含 vue3 / Vite CLI 项目）封装原生 SDK 为 UTS 插件；uni-app x 也可参考 UTS 部分但平台编译链不同，需注意差异。
- **不适用**：不涉及原生 SDK 的纯 JS 逻辑开发；uni-app x 的完整插件规范（本 skill 基于经典 uni-app 的 utssdk 目录约定）。

## 目录结构

```
uni-app-uts-native-sdk/
├── SKILL.md                        # 技能入口：完整方法论（目录规范、语法硬要点、API 设计、迁移、22 条踩坑）
├── README.md                       # 本文件：使用文档
└── （无 references/scripts/assets：方法论自包含于 SKILL.md）
```

## 深入阅读

- 📘 **完整使用文档**：[../../docs/uni-app-uts-native-sdk-使用文档.md](../../docs/uni-app-uts-native-sdk-使用文档.md)（按读者视角重组的一站式参考）
- [SKILL.md](SKILL.md)：agent 执行封装 / 迁移任务时的完整指令，含代码示例与逐条踩坑
