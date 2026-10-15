---
name: uni-app-uts-native-sdk
description: 用 uni-app UTS 插件封装三方原生 SDK（Android/iOS 双端统一 API），覆盖插件目录规范、原生依赖声明、协议/代理实现、权限申请与后台能力，以及把既有原生插件（aar/framework）迁移改造为 UTS 插件的完整方法论（契约反编译、调用点迁移、manifest 合并、回调诊断）。当用户要求"封装原生 SDK 成 uni-app 插件""UTS 插件对接高德/SDK""双端统一定位/地图/推送 API""utssdk app-android app-ios 怎么写""原生插件改 UTS""UTS 编译报错/回调不触发"时使用。
agent_created: true
---

# uni-app UTS 插件封装三方原生 SDK

目标：把 Android/iOS 原生 SDK 能力通过 UTS 暴露给 JS 层，**两端一套 API**，业务层不写 `#ifdef APP-PLUS`。

## 一、目录规范（API 插件）

```
uni_modules/<plugin-id>/
├── package.json                    id/displayName/version/uni_modules.platforms
└── utssdk/
    ├── interface.uts               类型 + 纯函数（类型与实现分离，两端共用）
    ├── index.uts                   非 App 端兜底（H5/小程序）
    ├── app-android/
    │   ├── config.json             Maven 依赖 / abis / minSdkVersion
    │   ├── AndroidManifest.xml     权限 + 组件/服务声明
    │   └── index.uts               实现（编译为 Kotlin）
    └── app-ios/
        ├── config.json             CocoaPods 依赖 / frameworks / deploymentTarget
        ├── info.plist              合并进主工程 Info.plist（权限描述、UIBackgroundModes）
        └── index.uts               实现（编译为 Swift）
```

要点：
- 分平台 `index.uts` 优先于 `utssdk/index.uts`；提供兜底文件可避免其他平台编译报错
- `interface.uts` 里 `export interface/type` 给 IDE 提示与跨端约束；页面里从插件根 import，不要直接 import interface.uts
- 所有平台配置**必须云打包/自定义基座**才生效，标准基座必然「未找到插件」

## 二、依赖声明（照抄这个格式）

Android `config.json`：
```json
{
  "abis": ["arm64-v8a", "armeabi-v7a"],
  "dependencies": ["com.amap.api:location:11.2.100"],
  "minSdkVersion": 21
}
```
iOS `config.json`：
```json
{
  "deploymentTarget": "12.0",
  "frameworks": ["CoreLocation", "SystemConfiguration"],
  "dependencies-pods": [{ "name": "AMapLocation", "version": "2.12.2" }]
}
```
- 查 Android 真实版本号：`curl -s https://repo1.maven.org/maven2/<group路径>/maven-metadata.xml`（别信文档正文里的版本）
- 查 iOS pod 版本：cocoapods.org 的 pod 页
- **不要重复声明传递依赖**（如 AMapFoundation），会 duplicate symbols

## 三、UTS 语法硬要点（实测）

| 场景 | 写法 |
| --- | --- |
| Android 实现原生接口 | `class X implements NativeInterface { override m(...): void {} }`，构造器 `super()` |
| iOS 遵循原生协议 | `implements NativeDelegate`（不是 extends），无需额外继承 NSObject |
| iOS 协议方法 | `amapLocationManager(manager: T, @argumentLabel("didUpdate") location: CLLocation)` —— `@argumentLabel` 标注 Swift 拆分出的参数标签 |
| iOS 协议方法多参数 | **每个参数都要显式标 `@argumentLabel`**。官方答复：多参数协议方法若只给第一个参数标注、后续参数留空，选择器拼不完整 → SDK 认不出你实现了它，会静默回落到另一个方法（如带逆地理的结果被无逆地理的版本替代） |
| iOS 协议重载 | 同名方法靠 `@argumentLabel` 区分多个协议方法（如 `didUpdate` / `didFailWithError` / `doRequireLocationAuth`）是可行的，但**必须真机验证**：写错不会报错，只是永远不回调 |
| iOS 带参数标签调用 | `mgr.requestLocation(withReGeocode = true, completionBlock = (a, b, c): void => {})` |
| 🔴 iOS 方法标签一律用 `=` 不用 `:` | `AVCaptureDevice.authorizationStatus(for = AVMediaType.video)` —— 写 Swift 风格 `for:` 直接报 `Expression expected`（UTS 是 TS 风格语法，标签是 `=`） |
| 🔴 iOS 不支持 trailing closure | `DispatchQueue.main.async { ... }` ✗ → `DispatchQueue.main.async(execute = (): void => { ... })` ✓；`renderer.image(actions = (ctx: T): void => { ... })` 同理，闭包必须走具名参数 |
| iOS 异常处理 | UTS 无 do-catch，统一 `try { } catch (e) { e.message }`；Swift throws 方法自动桥接为 UTS 异常，可直接用 try/catch 捕获 |
| iOS 构造器调用 | 自定义类用**位置参数**（`new CameraPickerDelegate(callback)`，不写标签）；系统类型保留标签（`new CGSize(width = ..., height = ...)`、`new URL(fileURLWithPath = ...)`） |
| 原生嵌套类 | 必须按完整路径单独 import：`import Builder from 'android.app.Notification.Builder'` |
| 原生类型 | 声明协议/接口方法签名时写 `Int` 等原生类型；**普通赋值/传参必须做显式数字转换，见第 3.1 节** |
| 权限申请 | `UTSAndroid.requestSystemPermission(act, perms, (allRight, perm) => {}, (neverAskAgain, perm) => {})` |
| 上下文 | `UTSAndroid.getAppContext()` / `UTSAndroid.getUniActivity()`（可能为 null，需判空） |
| 应用生命周期 | Android `export class AppHookProxy implements UTSAndroidHookProxy { override onCreate(app: Application) {} }`；iOS `implements UTSiOSHookProxy` |

### 3.1 🔴 数字类型转换（最容易在云打包时才炸的一类）

**UTS 不是 JS。** `number` 只是一个跨端类型别名——在 Android 上它编译为 **`kotlin.Number`**。UTS **不会**自动在 `number` 与平台专有数字类型之间转换，进出原生边界都必须显式处理。

**两条铁律 + 一类标注：**

```ts
// ① 原生数字 -> number：必须 Number.from()
//    ✗ 绝不能写 Number(x)：kotlin.Number 是抽象类，Number(x) 会被翻译成构造调用
//    报错：Cannot create an instance of an abstract class.
//          Too many arguments for 'constructor(): Number'.
//    官方：通过构造器创建 Number 仅支持 web 平台
result.accuracy = Number.from(location.getAccuracy())     // ✓
result.timestamp = Number.from(location.getLocationUtcTime())

// ② number -> 原生数字：必须 toXXX()
//    UTS 不会自动转换，直接传会报：
//    Argument type mismatch: actual type is 'Number', but 'Long' was expected.
option.setInterval(interval.toLong())                     // ✓
option.setHttpTimeOut(timeout.toLong())
builder.setWhen(Date.now().toLong())
PendingIntent.getActivity(context, NOTIFICATION_ID.toInt(), intent, flags)
client.enableBackgroundLocation(NOTIFICATION_ID.toInt(), notification)
manager.desiredAccuracy = accuracy.toDouble()
```

**转换对照表**（背下来，能省一轮云打包）：

| 方向 | 写法 | 兼容性 |
| --- | --- | --- |
| 原生 → `number` | `Number.from(x)` | Android 3.90+ / iOS 3.9+ |
| `number` → `Int` | `x.toInt()` | 双端 |
| `number` → `Long` | `x.toLong()` | **仅 Android** |
| `number` → `Double` | `x.toDouble()` | 双端 |
| `number` → `Float` | `x.toFloat()` | 双端 |

口诀：**「进 UTS 用 `Number.from`，出 UTS 用 `toXXX`」**。

**⚠️ 不要照抄 DCloud 官方 iOS 示例的 `Number(...)`。** `hello-uts` 的腾讯定位 iOS 实现里写的是 `Number(location.coordinate.latitude)`，该写法在 iOS 上可能因 `NSNumber` 桥接侥幸可用，但**在 Android 上必定编译失败**。两端统一用 `Number.from()`。

**🔴 第三类错误：UTS 变量赋给原生 Int 字段/参数（与①②并列，`compileReleaseKotlin` 才暴露）**

UTS 里数字字面量默认推断为 `number`（编译为 `kotlin.Number`），不是 Kotlin 的 `Int`：

```ts
let inSampleSize = 1                  // ✗ 推断为 number
options.inSampleSize = inSampleSize   // ✗ Assignment type mismatch: actual 'Number', but 'Int' was expected

let inSampleSize: Int = 1             // ✓ 凡赋给/传给原生 Int 字段或重载参数的变量，声明时显式 : Int
```

- 三元表达式结果无法标注时，拆成 if/else 用**字面量直传**匹配重载：`intent.putExtra(key, 0)` / `intent.putExtra(key, 1)`（字面量按重载推断为 Int）
- 只进 JSON 序列化（UTSJSONObject 字段、JSON.stringify）的数字无需标注——JS 侧收到的都是数字
- 扫描规则同下：交付前把所有「数字变量 → 原生 Int 字段/参数」的赋值点过一遍

**实践建议**：
1. 写原生调用时，对每个数字入参/出参都问一遍「这是 `number` 还是平台专有类型」。
2. 常见需要 `Long` 的：时间戳类（`setWhen(long)`）、间隔/超时类（`setInterval(long)`、`setHttpTimeOut(long)`）。
3. 常见需要 `Int` 的：id / requestCode / flags 类（`enableBackgroundLocation(int, …)`、`PendingIntent.getActivity(ctx, int, …)`）。
4. 交付前用脚本扫一遍：源码里出现 `Number(` 而非 `Number.from(` 就是 bug；`Number` 传给原生方法却无 `.toLong()/.toInt()` 也是 bug

**🔴 更重要的通用教训：别急着在插件层用 JS 补实现，先查一遍原生 SDK 有没有现成能力。**

反面案例：`distanceFilter` 一开始想当然认为「Android 没有原生对应项」，于是用 Haversine 在回调层做距离过筛。后来查官方 API 才发现高德有 **`setDeviceModeDistanceFilter(float)`（3.7.0+）**。

两者的区别不是"实现方式"，而是**省不省电**：

| 实现位置 | 省回调/JS 开销 | 省定位硬件耗电 |
| --- | --- | --- |
| 插件回调层过筛 | ✅ | ❌（SDK 仍按 interval 持续定位） |
| 原生 setter | ✅ | ✅（在系统定位回调这一环就丢弃） |

正确做法是**双层**：原生优先 + 回调层兜底。

⚠️ 原生能力常有**模式限制**，必须写进接口注释：`setDeviceModeDistanceFilter` 只对 `Device_Sensors` / `Hight_Accuracy` 生效，**`Battery_Saving` 不支持**。不写清楚，使用者会以为「传了参数就生效」。

同样的思路适用于所有"过滤/节流/去重"类需求：先查原生，再考虑 JS 兜底，最后才自己算。

## 四、后台能力清单（最容易漏）

**Android**
- 🔴 **权限必须「递增申请」，否则后台定位一定拿不到**：Android 11(API 30) 起 `ACCESS_BACKGROUND_LOCATION` **不能与任何其它权限放在同一次 `requestSystemPermission` 里**——系统不弹窗、直接拒绝，且不抛异常。正确顺序：①前台定位（FINE+COARSE）→ ②`POST_NOTIFICATIONS`（API 33+，也必须独占一批）→ ③`ACCESS_BACKGROUND_LOCATION`（独占一批）。
- 🔴 **Android 12+ 禁止在应用处于后台时启动前台服务** → 必须在 App 前台发起后台定位；`enableBackgroundLocation` 要包 `try/catch`，否则异常穿透到原生层会崩溃
- `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_LOCATION`（targetSdk 34）
- 服务声明 `android:foregroundServiceType="location"`；高德为 `<service android:name="com.amap.api.location.APSService">`
- 拉起前台服务：`AMapLocationClient.enableBackgroundLocation(notificationId, notification)`，通知渠道 IMPORTANCE_LOW；通知是**必需**的，不是可选
- 通知图标可用 `context.getApplicationInfo().icon` 免去 R 资源引用
- 通知务必加 `setContentIntent`（`PendingIntent.getActivity` + `FLAG_IMMUTABLE`）——Android 12+ 要求 PendingIntent 显式声明可变性，不加会崩；不加则点击通知无反应
- `disableBackgroundLocation(true)` 只关通知**不停止定位**，`stopLocation()` 只停定位**不关通知**，两者必须成对调用
- 「已加入电池优化白名单」是国产 ROM 后台存活的前提，用 `PowerManager.isIgnoringBatteryOptimizations(pkg)` 检测；引导页面用 `ACTION_APPLICATION_DETAILS_SETTINGS`（**不要**用 `ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`，Play 政策敏感易拒审）

**iOS**
- `Info.plist` 注入 `UIBackgroundModes: ["location"]`
- 🔴 **必须实现 `amapLocationManager(_:doRequireLocationAuth:)`**（高德类 SDK 的硬要求）：只要 plist 配了 Always 用途描述且状态为 `notDetermined` 就会走到这条路径，**不实现则权限弹窗根本不出现、系统设置里查不到定位项**，且只有一行容易被忽略的 SDK 警告。实现体里调 `requestAlwaysAuthorization()`
- 🔴 **`allowsBackgroundLocationUpdates` 只能在「定位开始之前」或「定位停止之后」修改**，运行中修改会被系统忽略 → start 时必须先设再 start；stop 时必须**先 stopUpdatingLocation 再置 false**，反了会导致后台标志位残留
- 🔴 **授权弹窗是异步的**：`notDetermined` 时不要立刻发起定位（必然失败）。挂起请求，等 `locationManagerDidChangeAuthorization`（iOS 14+）或 `didChangeAuthorizationStatus:`（iOS 13-）回调后再继续；用户拒绝要明确回错误，否则调用方永久 pending
- 权限需「始终允许」，仅「使用期间允许」时 `allowsBackgroundLocationUpdates=true` 是**无效**的，应降级为前台并告知
- 用户在持续定位**运行期间**才升级为 always 时不会自动补后台能力，必须 stop 再 start
- 三条用途描述文案必须具体（NSLocationWhenInUse / AlwaysAndWhenInUse / Always），否则上架易被拒

## 五、API 设计规范（对齐 uni 原生）

- 单次能力强同步回调三段式：`{ success, fail, complete }`
- 持续能力强 `onXxxChange(cb)` / `offXxxChange(cb?)` / `startXxxUpdate()` / `stopXxxUpdate()`
- 🔴 **必须有独立的运行期错误通道** `onXxxError(cb)` / `offXxxError(cb?)`。原因：`startXxxUpdate` 的 `success` 只代表「已启动」，启动之后的异常（权限被撤销、前台服务被系统回收、定位中断）**没有任何出口**。只在 `回调列表为空时` 才透出错误是不够的——真实业务一定注册了数据回调，错误会被彻底吞掉，表现为「以为在运行、实际早已断流」。
- 🔴 **区分「失败」与「能力降级」两种语义**：能力降级（如后台权限不足但前台定位已成功启动）不应该调用 `fail`，否则调用方看到「先失败后成功」的矛盾顺序。做法：降级原因先存到局部变量，等 `success` 抛出之后再通过**只投递给错误监听、不触发 fail** 的 `notifyError()` 抛出。
- 错误对象：`{ errCode: 联合字面量, errSubject: '插件id', errMsg }`，把两端原始错误码收敛成一套；错误码要预留「能力受限」类（如 1009）与平台能力受限场景
- 结果字段优先对齐 uni 同名 API（如 uni.getLocation 的 latitude/longitude/accuracy/altitude/speed/heading/timestamp），扩展字段附加在后
- 状态查询接口返回布尔能力位（如 `backgroundGranted` / `batteryOptimizationIgnored` / `updating`），让业务层能判断「是否需要引导用户去设置」——这比单纯报错更有用，因为权限被永久拒绝后重新申请是无效的
- 单次与持续能力互斥，用模块级状态变量做状态机，避免两端 SDK 行为冲突
- 🔴 **参数在各端语义必须一致**：若某参数在某端无原生对应项（如 Android 定位 SDK 没有 `distanceFilter`），要么在插件层自行实现补齐，要么在类型注释里写明「仅 X 端生效」。静默忽略是最糟的选择——同一份代码两端行为不同且无从排查

## 五之二、权限类插件必须提供「体检 + 导诊」（易漏，但用户最先撞到）

只返回错误码是不够的。用户看到「定位失败」时，**根因通常有三种，且要去的设置页完全不同**——不区分的话用户根本找不到开关，还会以为插件坏了。

设计一个同步的体检函数，把多个布尔状态收敛成**一个明确的下一步动作**：

```ts
checkXxxReady(options?) => {
  ready: boolean,
  issue: 'none' | 'needRequestPermission' | 'needOpenPermissionSettings' | 'needOpenLocationService' | 'needOpenBatterySettings' | ...,
  canRequestPermission: boolean,   // ★ 最关键：为 false 时再调用多少次 API 都不会弹窗
  settingsType: 'permission' | 'locationService' | 'battery',
  message: string,                 // 已按原因生成好的用户文案
  permission: XxxPermissionResult
}
```

判定**优先级**很重要（顺序错了会给出无效引导）：
```
系统总开关 → 基础权限 → 后台权限 → 省电策略
```
总开关没开时，权限给了也没用，必须先引导去开总开关。

设置页跳转必须**分场景精确路由**，跳错等于没跳：
- `permission` → Android `ACTION_APPLICATION_DETAILS_SETTINGS`（带 `package:` data）/ iOS `app-settings:`
- `locationService` → Android `ACTION_LOCATION_SOURCE_SETTINGS`（**应用详情页里没有总开关**）
- `battery` → Android `ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS`
- 跳转失败要**逐个降级**到最后兜底应用详情页，ROM 可能裁剪了设置页

**iOS 平台限制**：系统级定位/隐私总开关**没有公开深链**（`App-Prefs:` 是私有 API，用了有 App Store 拒审风险），只能给文案引导。不要为了"体验好"去用私有 API。

**区分「没申请过」与「已被拒绝」**，两者动作相反：前者直接调 API 就会弹窗（不要打扰用户），后者重试 100% 无效（必须去设置页）。Android 用 `requestSystemPermission` 的 `neverAskAgain` 回调 + 自记 `hasRequestedPermission`；iOS 看 `status == notDetermined`。

**边界**：插件只做「体检 + 导诊」（返回结构化结果，不引入 UI 依赖），弹窗交给调用方的 `uni.showModal`。这样跨端一致、文案与样式可定制，也避免在插件里操作 UI 线程。

## 五之三、后台能力（定位/轨迹/上传）的封装：先想清楚生命周期归属

**动手封装前先问一句：这个能力的生命周期归谁？** 答案不同，封装形态完全不同。

| | 前台持续能力 | 后台持续能力 |
| --- | --- | --- |
| 生命周期归属 | **页面** | **App / 一次业务任务** |
| 页面 `onUnmounted` 该做什么 | 停掉它 | **只解绑 UI 回调，不停它** |
| 结束时机 | 离开页面 | 业务终点（任务完成 / 用户手动结束 / 登出） |

把后台能力写进页面 `onUnmounted` 里 stop，等于把它降级成前台能力——熄屏、切页就断，整个功能失去意义。

归属不同 → 封装层必须额外解决三件事（做成**模块级单例开关**，不要每次调用临时注册）：

1. **幂等**：首页恢复、按钮、定时任务等多个入口会重复调用 → 回调堆成多层 → 数据重复上报。做法：启动前先检测运行状态，已运行则先停再启。
2. **单例**：全局只能有一份数据流，避免多份 track 互相污染。
3. **可查询**：页面重建 / 冷启动后要能知道「现在到底在不在运行」。**查询必须读原生状态，不能用 JS 内存布尔值**（页面重建或进程重启后内存值就丢了）。

**推荐的调用方范式——把「数据上报」和「UI 渲染」拆成两个回调**：

- 上报回调由 **App 层**持有（后台持续期间一直执行）
- 渲染回调由 **页面**持有（`onUnmounted` 只解绑它）

很多项目写得别扭，根因就是把这两件事混在一个回调里：页面卸载时不敢解绑（怕丢数据），只好连能力一起停掉。拆开之后，页面卸载只是"不再刷新列表"，能力继续跑。

**启动函数的实现顺序也有讲究**：
```
① 幂等清理（停旧的 / 解绑旧回调）
② 就绪检查 + 引导（用户可能点「暂不」→ 这里直接抛错返回）
③ 注册回调 + 真正启动
```
把 ② 放在 ③ 之前，可以避免出现「已注册回调但没启动」的中间态；启动失败也要回滚第 ③ 步已注册的回调。

**最后一条硬约束**：Android 12+ 禁止后台应用启动前台服务。所以「到点自动开始」这类需求，正确做法是在**用户进入 App 时**启动并保持，而不是指望后台定时唤醒去启动它。

## 五之四、把既有原生插件（aar/framework）改造为 UTS 插件（迁移方法论）

用户最常见的诉求是「调用方式和返回方式跟旧插件保持一致」。一致性不是猜出来的，是**反编译还原出来的**。

### 1. 契约还原：先反编译，再动手

- **Android aar**：`unzip xxx.aar` 取 `classes.jar` → `javap -p -classpath cls com.xxx.YourModule` 看方法签名；`javap -c -p` 看字节码还原**错误码常量值、成功回调字段、参数到原生枚举的映射**（常量池字符串会暴露 `"error"`/`"success"`/`"path"` 等 JSON 字段名与 `JSONObject.put` 调用序列）
- **iOS framework**：`nm -gU` 看 ObjC 符号——类名、IVar（`_useFrontCamera`、`_imagePicker`）、遵循的协议（`UIImagePickerControllerDelegate`）一眼定位实现方式
- 必须还原的**隐性契约**（最容易漏的）：
  - 回调数据形态：JSON **字符串**（`JSON.stringify` 后回调）还是对象？业务侧 `typeof data == 'string'` 分支会暴露真相
  - 用户取消拍照/选择时**是否回调**（很多旧插件取消是静默的，新插件必须保持一致，否则业务侧逻辑对不上）
  - 文件路径是否带 `file://` 前缀
  - 错误码数值表（10001/10002/10003…各对应什么）
- 调用方业务代码的**回调体一行都不要动**，只替换插件获取方式

### 2. 调用点按「插件名 + 方法名」全局扫所有文件类型

```
grep -rn "插件名\|方法名" --include="*.vue" --include="*.js" --include="*.ts" --include="*.uts" --include="*.nvue" 全项目
```

- 🔴 范围是**全项目**，不是只搜 `requireNativePlugin` + pages 目录——**三方组件藏在 uni_modules 里**（实战踩坑：上传组件 `uni_modules/cc-imgPreDelUpload` 内部也调了原生相机插件，漏改 = 运行时 `requireNativePlugin` 返回 undefined → `Cannot read property 'openFrontCamera' of undefined`）
- 改完再扫一遍确认 0 残留，`requireNativePlugin('旧插件名')` 和 `旧实例.方法名` 两个模式都要扫

### 3. Manifest 合并：资源能搬，authority 唯一

- UTS 插件的 `app-android/AndroidManifest.xml` 会合并进主工程：权限、`<queries>`（Android 11+ 包可见性，`resolveActivity` 系统相机必需）、`<provider>` 都可以声明；`res/xml/` 资源文件随插件合并
- 🔴 **FileProvider authority 全局唯一**：新旧插件并存、都声明 `${applicationId}.fileprovider` → Manifest Merge 冲突，**云打包必失败**。迁移完成后必须从 `manifest.json` 的 `plugins` + `nativePlugins` 两处移除旧插件注册
- `resolveActivity` 在 Android 11+ 受包可见性限制，插件的 manifest 里加 `<queries><intent><action android:name="android.media.action.IMAGE_CAPTURE"/></intent></queries>` 双保险

### 4. Activity 结果回传类插件的结果监听范式（onAppActivityResult，Android 真机全链路验证 ✓）

**适用范围不限于拍照/选图**：凡通过 `startActivityForResult` 拉起外部 Activity 并需要把结果回传 JS 的场景都走这套范式——系统相机/相册（ACTION_IMAGE_CAPTURE / ACTION_PICK）、SAF 文件选择（OPEN_DOCUMENT）、三方授权登录（微信/QQ）、支付结果页、地图 POI 选点、人脸识别/OCR 拍摄 SDK、系统设置页返回等。共同结构：**发起时拿到 JS callback → startActivityForResult → 异步结果 → 靠模块级 pendingCallback 桥回 JS**。

```ts
let pendingCallback: ((res: any | null) => void) | null = null
let listenerRegistered = false

function registerResultListener() {
  if (listenerRegistered) return           // 模块级幂等，只注册一次
  listenerRegistered = true
  UTSAndroid.onAppActivityResult((requestCode: Int, resultCode: Int, data: Intent | null) => {
    console.log('[插件前缀] onActivityResult:', requestCode, resultCode)  // 🔴 每一步都要有日志
    if (requestCode != MY_REQUEST_CODE) return
    const cb = pendingCallback
    pendingCallback = null
    if (cb == null) {
      console.log('[插件前缀] 无待处理回调')
      return
    }
    if (resultCode == Activity.RESULT_OK) {   // RESULT_OK = -1，取消 = 0
      const finalPath = compress(currentPath)
      console.log('[插件前缀] 成功, path=', finalPath)
      cb(JSON.stringify({ success: true, path: finalPath }))
      console.log('[插件前缀] 成功回调已发出')
    } else {
      console.log('[插件前缀] 用户取消 resultCode=', resultCode, '（跟原契约：不回调）')
    }
  })
}

function startCamera(callback: (res: any | null) => void) {
  // ... 构建 Intent / FileProvider ...
  pendingCallback = callback            // 🔴 发起调用前挂载回调——声明了、读了、漏了赋值 = 永远拿不到结果
  registerResultListener()              // 注册必须在 startActivityForResult 之前
  activity.startActivityForResult(intent, MY_REQUEST_CODE)
}
```

- 🔴 **回调体里每一步都要打日志**（收到的原始 requestCode/resultCode、压缩前后路径、回调是否发出）——「JS 调用了但没回调」的排查三板斧：①确认手机跑的是新 JS（业务侧加打印）②确认运行时选的是含插件的**自定义基座** ③在 UTS 回调链每一环加日志。**回调体里没日志就是排查盲区**
- ✅ **真机验证结论（2026-10 实测）**：宿主对 `onAppActivityResult` **原样传递 requestCode**（发 1101 收 1101）与 resultCode（拍照确认收 -1）；`requestSystemPermission` 已授权场景直接同步回调 allRight=true；系统相机 `ACTION_IMAGE_CAPTURE` + `EXTRA_OUTPUT(FileProvider)` + maxWidth 压缩 + JSON 字符串回调全链路可用
- 诊断技巧（本轮定位根因时验证）：把回调体每个分支都加日志后，`requestCode`/`resultCode`/`pendingCallback` 三者谁有问题一目了然——曾据此定位到「pendingCallback 声明/读取都在但赋值遗漏」的低级 bug（见踩坑 22）

### 5. 交付自检（本轮实战验证有效）

- 按 3.1 扫三类数字错误：`Number(` 误用 / `number` 直传原生参数 / **字面量推断赋给原生 Int 字段**
- UTSAndroid API 有编译期校验：编译通过 = API 名存在；**运行期回调不触发不是 API 名写错**，按上面三板斧查
- 模块级状态变量（pendingCallback 等）逐个确认「有声明 + 有读取 + **有写入**」三件套（见踩坑 22）
- iOS delegate 签名、泛型字典类型等**无法本地验证**的点，readme 里显式列为「真机验证清单」（delegate 签名不匹配不报错、只静默不回调）

## 六、踩坑清单

1. 文档正文的 SDK 版本号常常滞后/自相矛盾 → 以 Maven metadata / pod 页为准
2. iOS 的 `@argumentLabel` 写错 → 代理永远不回调，且没有任何报错
3. Android 权限必须用 `Array<string>` 且 `UTSAndroid.getUniActivity()` 判空
4. 隐私合规接口（updatePrivacyShow/updatePrivacyAgree）与 apiKey 都必须在 SDK 实例化**之前**调用，顺序错了静默失效
5. 页面 `onUnmounted` 必须 `offXxxChange()` + `stopXxxUpdate()`，否则回调残留
6. 工程交付时在 README 里显式列出「依赖原生类名/签名的互操作点」及替代方案，排查成本远低于让使用者自己猜
7. 🔴 **改原生 SDK 前先 grep 接口文件，确认实现里引用的每个 option 字段都在 interface 里声明过**。UTS 是强类型的，引用未声明字段会编译失败；本次就踩到 iOS 实现引用了 `desiredAccuracy` 而 interface 里没有
8. 🔴 **「能编译」不等于「能用」**：权限类功能尤其如此。Android 后台定位权限同批申请、iOS 缺 `doRequireLocationAuth`，两者都不报任何错，但功能 100% 不工作。交付前必须按「权限弹窗是否出现 / 系统设置里能否看到权限项 / 熄屏后是否仍有回调」三步实测
9. 🔴 **操作系统层面无法保证的不要写在文档里当承诺**：App 被强杀后双端都无法仅靠插件自动恢复定位（iOS 需 significantLocationChanges 或静默推送，Android 需厂商推送 + 用户开启自启动）。要明确告知业务侧方案边界，并提供「断流可感知」的错误通道作为方案的一环
10. 后台耗电的第一大开关是**距离过滤**而非采样间隔——它直接决定回调频率。没有原生距离过滤能力的平台要在插件层用 Haversine 过筛
11. 🔴 **别把「返回错误码」当成「做好了权限处理」**。用户看到的只是「定位失败」，而原因有三种、设置页各不相同。必须提供体检 + 分场景跳转（见第五之二节）。否则同一个问题会在每个接入项目里被重复问一遍
12. 交付权限类插件前，逐条走一遍「未授权 / 已拒绝 / 已被永久拒绝 / 系统总开关关闭 / 省电白名单未放行」五种初始状态，确认每种都能给出**可执行的**引导，而不是一句通用报错
13. 🔴 **`Number(x)` 与「`number` 直传原生数字参数」是云打包才会炸的两类错误**（见第 3.1 节）。静态看语法完全合法，IDE 也不一定报错，只有 `compileReleaseKotlin` 才暴露。写原生调用时按「进 `Number.from` / 出 `toXXX`」逐个数一遍
14. 遇到 `Project with path ':uni_modules:xxx' could not be found` 先别急着查那个模块——**多半是另一个 UTS 插件编译失败的连带现象**（编译中断导致该模块的 Gradle 子工程没生成）。往上翻日志找第一个 `compileReleaseKotlin` 失败才是真正根因
15. 🔴 **`offXxxChange(cb)` 按引用相等移除回调，内联箭头函数一定解绑不掉**：
    ```ts
    onXxxChange((res) => list.push(res))     // ✗ 两次创建的是不同函数对象
    offXxxChange((res) => list.push(res))    // 摘除失败 → 回调残留在已销毁的页面上
    ```
    后果隐蔽：页面已销毁仍在执行，表现为「进几次该页面后开始卡/报错」，不会立刻暴露。
    **两种解法**：① 用命名函数；② 更稳的做法是在插件/封装层提供一个「作用域安全」的注册函数，内部固定引用并**返回解绑函数**——把引用稳定性从调用方手里拿走：
    ```ts
    export function attachXxxListener(cb: (res: any) => void): () => void {
      onXxxChange(cb)
      return () => offXxxChange(cb)      // 闭包捕获同一引用，必然能摘除
    }
    ```
16. 设计「持续能力」的调用方范式时，**把「数据持久化/上报」与「UI 渲染」拆成两个回调**，二者同时注册、都会被调用，区别只在解绑时机。合成一个会二选一地失败：注册在 App 层 → 页面卸载后改已销毁状态；注册在页面层 → 上报也跟着停，能力空跑且**不报错**（最难排查的一种）
17. 🔴 **iOS 方法调用参数标签用 `=` 不用 `:`**（`authorizationStatus(for = AVMediaType.video)`）——写 Swift 风格 `for:` 直接 `Expression expected`；trailing closure 同理不支持（`async { }` ✗ → `async(execute = ...)` ✓），闭包一律走具名参数
18. 🔴 **UTS 数字字面量推断为 `number`**：`let x = 1` 赋给原生 Int 字段 = `Assignment type mismatch: actual Number, but Int expected`（本地 IDE 不报错，`compileReleaseKotlin` 才暴露）。显式 `: Int` 标注，或 if/else 拆开用字面量直传匹配重载
19. 🔴 **迁移原生插件时按「插件名+方法名」全项目扫所有文件类型**——三方组件可能藏在 uni_modules 深处，漏一个就是运行时 `undefined` 崩溃（且报错行号在新代码里根本不存在，说明手机跑的还是旧 JS）
20. **FileProvider authority（`${applicationId}.fileprovider`）全局唯一**：新旧插件并存双声明 = Manifest Merge 冲突云打包失败；UTS 插件的 manifest 可以声明 provider/queries/权限并合并进主工程
21. **「JS 调了但没回调」排查三板斧**：①业务侧加打印确认跑的是新 JS（报错形态/行号对不上新代码 = 旧 JS 没推送或 apk 里打的是旧 JS）②确认运行时选的是含插件的**自定义基座**（桥接找不到插件会静默失败）③UTS 回调链每一环打日志（`[前缀]` 便于过滤），回调体里没日志是排查盲区
22. 🔴 **回调挂载遗漏**：`onActivityResult` 类异步回调的插件，模块级 `pendingCallback` 声明了、回调体里读了，但**发起调用时忘了赋值**（`pendingCallback = callback`）——表现为「请求成功发出、结果正确到达、回调体也执行了，却永远拿不到 callback」。自查方法：**每个被读取的模块级状态变量，确认至少有一个写入点**；且赋值要在 `startActivityForResult` 之前完成

## 七、编译运行与调试（HBuilderX）

**核心心智模型**：`index.uts` 在编译期被转成 Kotlin/Swift 编进基座包，运行时读的是基座里那份。

> **改了 `utssdk/app-*/index.uts` 任何一行原生代码 → 必须重做自定义基座。只改 JS/页面代码不用重做。**

流程：`运行 → 运行到手机或模拟器 → 制作自定义调试基座`（选平台、勾原生插件、云端打包 5~15 分钟，iOS 更久因为要 pod install）→ 打包完成后再 `运行到 Android/iOS App 基座`，选「自定义基座」。

其他要点：
- CLI（vue-cli/Vite）项目也要用 HBuilderX「打开目录」来跑，UTS 原生编译链路依赖 HBuilderX
- 环境要求：HBuilderX ≥ 3.8.5（`dependencies-pods` 需此版本）；macOS 上 iOS 真机运行需本地装有 CocoaPods
- 调试技巧：给 `utssdk/index.uts` 写一套委托 `uni.getXxx` 的兜底实现，就能在 H5 端先调 UI 逻辑，不用每次等基座
- 建议同时写一份 `docs/USAGE.md` 操作手册，把「改了代码要不要重做基座」「Key 的包名+SHA1 绑定」「后台定位 6 项检查」这类高频问题前置说明，能显著降低使用者求助成本

**第三方 Key 类 SDK 的通用坑**：Android Key 校验的是「包名 + 签名 SHA1」组合，调试证书与发布证书 SHA1 不同 → 出现"调试能定位、正式包定位失败"。README/USAGE 里要提醒为同一包名配两把 Key 或统一用同一证书。
