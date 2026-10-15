# uni-app UTS 插件封装原生 SDK 使用文档

> 本文是 `uni-app-uts-native-sdk` skill 的完整使用文档，覆盖从插件目录搭建、依赖声明、原生代码编写、权限与后台能力、API 设计，到旧插件迁移、编译调试、交付自检的全链路。
> 所有结论均来自真实云打包实测；凡标注 🔴 的是「不报错但功能 100% 不工作」或「云打包才炸」的高危项。
> 面向读者：**要封装原生 SDK 的开发者**、**要迁移旧原生插件的开发者**、**插件使用方**。

---

## 一、心智模型：UTS 插件到底是什么

```
JS 层（页面 / 组件）
    ↓ import（从插件根目录，如 uni_modules/xxx）
interface.uts —— 类型 + 纯函数，两端共用的契约
    ↓ 编译期分发
app-android/index.uts ──→ 编译为 Kotlin ──→ 打进基座 apk
app-ios/index.uts     ──→ 编译为 Swift ──→ 打进基座 ipa
utssdk/index.uts      ──→ H5 / 小程序兜底实现（可选，提供可避免其他平台编译报错）
```

三条基本认知，所有章节都建立在它们之上：

1. **`index.uts` 是编译期产物**：改任何一行原生代码 → 必须重做自定义基座；只改 JS / 页面代码不用。
2. **标准基座必然「未找到插件」**：所有平台配置（依赖、权限、Info.plist）只有云打包 / 自定义基座才生效。
3. **UTS 不是 JS**：它是 TS 风格语法、编译为 Kotlin / Swift 的强类型语言。JS 里的隐式转换、动态类型直觉全部不适用——这是本文第三章存在的原因。

---

## 二、插件目录规范（API 插件）

```
uni_modules/<plugin-id>/
├── package.json                    # id / displayName / version / uni_modules.platforms
└── utssdk/
    ├── interface.uts               # 类型 + 纯函数（类型与实现分离，两端共用）
    ├── index.uts                   # 非 App 端兜底（H5 / 小程序）
    ├── app-android/
    │   ├── config.json             # Maven 依赖 / abis / minSdkVersion
    │   ├── AndroidManifest.xml     # 权限 + 组件 / 服务声明（合并进主工程）
    │   └── index.uts               # 实现（编译为 Kotlin）
    └── app-ios/
        ├── config.json             # CocoaPods 依赖 / frameworks / deploymentTarget
        ├── info.plist              # 合并进主工程 Info.plist（权限描述、UIBackgroundModes）
        └── index.uts               # 实现（编译为 Swift）
```

要点：

- 分平台 `index.uts` 优先于 `utssdk/index.uts`；提供兜底文件可避免其他平台编译报错；
- `interface.uts` 里 `export interface/type` 给 IDE 提示与跨端约束；**页面里从插件根 import，不要直接 import `interface.uts`**；
- 🔴 **改原生 SDK 前先 grep 接口文件**，确认实现里引用的每个 option 字段都在 interface 里声明过——UTS 是强类型，引用未声明字段直接编译失败（实战踩过：iOS 实现引用 `desiredAccuracy` 而 interface 里没有）。

---

## 三、依赖声明

### 3.1 Android config.json

```json
{
  "abis": ["arm64-v8a", "armeabi-v7a"],
  "dependencies": ["com.amap.api:location:11.2.100"],
  "minSdkVersion": 21
}
```

### 3.2 iOS config.json

```json
{
  "deploymentTarget": "12.0",
  "frameworks": ["CoreLocation", "SystemConfiguration"],
  "dependencies-pods": [{ "name": "AMapLocation", "version": "2.12.2" }]
}
```

### 3.3 版本号与依赖规则

- 查 Android 真实版本号：`curl -s https://repo1.maven.org/maven2/<group路径>/maven-metadata.xml`——**别信文档正文里的版本**（实测滞后 / 自相矛盾是常态）；
- 查 iOS pod 版本：cocoapods.org 的 pod 页；
- 🔴 **不要重复声明传递依赖**（如 AMapFoundation），会 duplicate symbols；
- 环境要求：HBuilderX ≥ 3.8.5（`dependencies-pods` 需此版本）；macOS 上 iOS 真机运行需本地装有 CocoaPods。

---

## 四、UTS 语法硬要点

### 4.1 🔴 数字类型转换（头号坑，云打包才炸）

**UTS 不是 JS。** `number` 只是跨端类型别名——在 Android 上编译为 `kotlin.Number`。UTS **不会**自动在 `number` 与平台专有数字类型之间转换，进出原生边界都必须显式处理。

```ts
// ① 原生数字 → number：必须 Number.from()
//    ✗ 绝不能写 Number(x)：kotlin.Number 是抽象类，Number(x) 会被翻译成构造调用
//    报错：Cannot create an instance of an abstract class.
result.accuracy = Number.from(location.getAccuracy())     // ✓
result.timestamp = Number.from(location.getLocationUtcTime())

// ② number → 原生数字：必须 toXXX()
//    直接传会报：Argument type mismatch: actual type is 'Number', but 'Long' was expected.
option.setInterval(interval.toLong())                     // ✓
option.setHttpTimeOut(timeout.toLong())
builder.setWhen(Date.now().toLong())
PendingIntent.getActivity(context, NOTIFICATION_ID.toInt(), intent, flags)
manager.desiredAccuracy = accuracy.toDouble()
```

**转换对照表**（背下来，能省一轮云打包）：

| 方向 | 写法 | 兼容性 |
|---|---|---|
| 原生 → `number` | `Number.from(x)` | Android 3.90+ / iOS 3.9+ |
| `number` → `Int` | `x.toInt()` | 双端 |
| `number` → `Long` | `x.toLong()` | **仅 Android** |
| `number` → `Double` | `x.toDouble()` | 双端 |
| `number` → `Float` | `x.toFloat()` | 双端 |

口诀：**「进 UTS 用 `Number.from`，出 UTS 用 `toXXX`」**。

> ⚠️ **不要照抄 DCloud 官方 iOS 示例的 `Number(...)`**：`hello-uts` 的腾讯定位 iOS 实现写的是 `Number(location.coordinate.latitude)`，该写法在 iOS 上可能因 `NSNumber` 桥接侥幸可用，但**在 Android 上必定编译失败**。两端统一用 `Number.from()`。

### 4.2 🔴 第三类错误：UTS 变量赋给原生 Int 字段（与①②并列）

UTS 里数字字面量默认推断为 `number`（编译为 `kotlin.Number`），不是 Kotlin 的 `Int`：

```ts
let inSampleSize = 1                  // ✗ 推断为 number
options.inSampleSize = inSampleSize   // ✗ Assignment type mismatch: actual 'Number', but 'Int' was expected

let inSampleSize: Int = 1             // ✓ 赋给原生 Int 字段/重载参数的变量，声明时显式 : Int
```

- 三元表达式结果无法标注时，拆成 if/else 用**字面量直传**匹配重载：`intent.putExtra(key, 0)` / `intent.putExtra(key, 1)`（字面量按重载推断为 Int）；
- 只进 JSON 序列化（UTSJSONObject 字段、`JSON.stringify`）的数字无需标注——JS 侧收到的都是数字。

**常见需要 `Long` 的**：时间戳类（`setWhen(long)`）、间隔 / 超时类（`setInterval(long)`、`setHttpTimeOut(long)`）。
**常见需要 `Int` 的**：id / requestCode / flags 类（`enableBackgroundLocation(int, …)`、`PendingIntent.getActivity(ctx, int, …)`）。

### 4.3 iOS 专项语法

| 场景 | 写法 |
|---|---|
| 🔴 方法标签一律用 `=` 不用 `:` | `AVCaptureDevice.authorizationStatus(for = AVMediaType.video)`——写 Swift 风格 `for:` 直接 `Expression expected` |
| 🔴 不支持 trailing closure | `DispatchQueue.main.async { }` ✗ → `async(execute = (): void => { })` ✓；闭包一律走具名参数 |
| 遵循原生协议 | `implements NativeDelegate`（不是 extends），无需额外继承 NSObject |
| 协议方法 | `amapLocationManager(manager: T, @argumentLabel("didUpdate") location: CLLocation)` |
| 🔴 协议方法多参数 | **每个参数都要显式标 `@argumentLabel`**。只标第一个、后续留空 → 选择器拼不完整 → SDK 认不出你实现了它，静默回落到另一个方法 |
| 带参数标签调用 | `mgr.requestLocation(withReGeocode = true, completionBlock = (a, b, c): void => {})` |
| 异常处理 | UTS 无 do-catch，统一 `try { } catch (e) { e.message }`；Swift throws 自动桥接为 UTS 异常 |
| 构造器调用 | 自定义类用**位置参数**（`new CameraPickerDelegate(callback)`）；系统类型保留标签（`new CGSize(width = ..., height = ...)`） |

**协议重载靠 `@argumentLabel` 区分**（如 `didUpdate` / `didFailWithError` / `doRequireLocationAuth`）可行，但**必须真机验证**：写错不会报错，只是永远不回调。

### 4.4 Android 专项语法

| 场景 | 写法 |
|---|---|
| 实现原生接口 | `class X implements NativeInterface { override m(...): void {} }`，构造器 `super()` |
| 原生嵌套类 | 必须按完整路径单独 import：`import Builder from 'android.app.Notification.Builder'` |
| 原生类型 | 声明协议 / 接口方法签名时写 `Int` 等原生类型；普通赋值 / 传参必须显式转换（见 4.1 / 4.2） |
| 权限申请 | `UTSAndroid.requestSystemPermission(act, perms, (allRight, perm) => {}, (neverAskAgain, perm) => {})` |
| 上下文 | `UTSAndroid.getAppContext()` / `UTSAndroid.getUniActivity()`（**可能为 null，需判空**） |
| 应用生命周期 | `export class AppHookProxy implements UTSAndroidHookProxy { override onCreate(app: Application) {} }` |

### 4.5 通用教训：别急着在插件层用 JS 补实现

反面案例：`distanceFilter` 想当然认为「Android 没有原生对应项」，用 Haversine 在回调层过筛；后查官方 API 才发现高德有 `setDeviceModeDistanceFilter(float)`（3.7.0+）。

| 实现位置 | 省回调/JS 开销 | 省定位硬件耗电 |
|---|---|---|
| 插件回调层过筛 | ✅ | ❌（SDK 仍按 interval 持续定位） |
| 原生 setter | ✅ | ✅（在系统定位回调这一环就丢弃） |

正确做法是**双层**：原生优先 + 回调层兜底。且原生能力常有**模式限制**（`setDeviceModeDistanceFilter` 只对 `Device_Sensors` / `Hight_Accuracy` 生效，`Battery_Saving` 不支持），必须写进接口注释。所有「过滤 / 节流 / 去重」类需求同理：**先查原生，再考虑 JS 兜底，最后才自己算**。

---

## 五、权限申请与后台能力（最容易漏）

### 5.1 Android：权限必须「递增申请」

🔴 Android 11 (API 30) 起 `ACCESS_BACKGROUND_LOCATION` **不能与任何其它权限放在同一次 `requestSystemPermission` 里**——系统不弹窗、直接拒绝，且不抛异常。正确顺序，每批独占一次：

1. 前台定位（FINE + COARSE）
2. `POST_NOTIFICATIONS`（API 33+，也必须独占一批）
3. `ACCESS_BACKGROUND_LOCATION`（独占一批）

其他硬性项：

- 🔴 **Android 12+ 禁止应用处于后台时启动前台服务** → 必须在 App 前台发起后台定位；`enableBackgroundLocation` 要包 `try/catch`，否则异常穿透到原生层会崩溃；
- `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_LOCATION`（targetSdk 34）；服务声明 `android:foregroundServiceType="location"`；
- 通知渠道 IMPORTANCE_LOW；通知是**必需**的，不是可选；图标可用 `context.getApplicationInfo().icon` 免去 R 资源引用；
- 通知务必加 `setContentIntent`（`PendingIntent.getActivity` + `FLAG_IMMUTABLE`）——Android 12+ 要求 PendingIntent 显式声明可变性，不加会崩；
- `disableBackgroundLocation(true)` 只关通知**不停止定位**，`stopLocation()` 只停定位**不关通知**，两者必须成对调用；
- 「已加入电池优化白名单」是国产 ROM 后台存活的前提，用 `PowerManager.isIgnoringBatteryOptimizations(pkg)` 检测；引导用 `ACTION_APPLICATION_DETAILS_SETTINGS`（**不要**用 `ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`，Play 政策敏感易拒审）。

### 5.2 iOS：后台定位三红线

- 🔴 **必须实现 `amapLocationManager(_:doRequireLocationAuth:)`**（高德类 SDK 硬要求）：plist 配了 Always 用途描述且状态为 `notDetermined` 就会走这条路径，**不实现则权限弹窗根本不出现、系统设置里查不到定位项**，且只有一行容易被忽略的 SDK 警告。实现体里调 `requestAlwaysAuthorization()`；
- 🔴 **`allowsBackgroundLocationUpdates` 只能在「定位开始之前」或「定位停止之后」修改**：start 时必须先设再 start；stop 时必须**先 `stopUpdatingLocation` 再置 false**，反了会导致后台标志位残留；
- 🔴 **授权弹窗是异步的**：`notDetermined` 时不要立刻发起定位（必然失败）。挂起请求，等 `locationManagerDidChangeAuthorization`（iOS 14+）或 `didChangeAuthorizationStatus:`（iOS 13-）回调后再继续；用户拒绝要明确回错误，否则调用方永久 pending；
- `Info.plist` 注入 `UIBackgroundModes: ["location"]`；三条用途描述文案（WhenInUse / AlwaysAndWhenInUse / Always）必须具体，否则上架易被拒；
- 权限需「始终允许」，仅「使用期间允许」时 `allowsBackgroundLocationUpdates = true` **无效**，应降级为前台并告知；用户在定位**运行期间**才升级为 always 时不会自动补后台能力，必须 stop 再 start。

### 5.3 权限类插件必须提供「体检 + 导诊」

只返回错误码是不够的。用户看到「定位失败」时，**根因通常有三种，且要去的设置页完全不同**。设计一个同步体检函数，把多个布尔状态收敛成**一个明确的下一步动作**：

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

判定**优先级**（顺序错了会给出无效引导）：

```
系统总开关 → 基础权限 → 后台权限 → 省电策略
```

总开关没开时，权限给了也没用，必须先引导去开总开关。

设置页跳转必须**分场景精确路由**，跳错等于没跳：

- `permission` → Android `ACTION_APPLICATION_DETAILS_SETTINGS`（带 `package:` data）/ iOS `app-settings:`
- `locationService` → Android `ACTION_LOCATION_SOURCE_SETTINGS`（**应用详情页里没有总开关**）
- `battery` → Android `ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS`
- 跳转失败要**逐个降级**到最后兜底应用详情页（ROM 可能裁剪了设置页）

**iOS 平台限制**：系统级定位 / 隐私总开关**没有公开深链**（`App-Prefs:` 是私有 API，有拒审风险），只能给文案引导。

**区分「没申请过」与「已被拒绝」**：前者直接调 API 就会弹窗（不要打扰用户），后者重试 100% 无效（必须去设置页）。Android 用 `requestSystemPermission` 的 `neverAskAgain` 回调 + 自记 `hasRequestedPermission`；iOS 看 `status == notDetermined`。

**边界**：插件只做「体检 + 导诊」（返回结构化结果，不引入 UI 依赖），弹窗交给调用方的 `uni.showModal`。

### 5.4 后台能力的生命周期归属

动手封装前先问一句：**这个能力的生命周期归谁？**

| | 前台持续能力 | 后台持续能力 |
|---|---|---|
| 生命周期归属 | **页面** | **App / 一次业务任务** |
| 页面 `onUnmounted` 该做什么 | 停掉它 | **只解绑 UI 回调，不停它** |
| 结束时机 | 离开页面 | 业务终点（任务完成 / 用户手动结束 / 登出） |

把后台能力写进页面 `onUnmounted` 里 stop，等于把它降级成前台能力——熄屏、切页就断，整个功能失去意义。

归属不同，封装层必须额外解决三件事（做成**模块级单例开关**，不要每次调用临时注册）：

1. **幂等**：首页恢复、按钮、定时任务多个入口重复调用 → 回调堆成多层 → 数据重复上报。启动前先检测运行状态，已运行则先停再启；
2. **单例**：全局只能有一份数据流；
3. **可查询**：页面重建 / 冷启动后要能知道「现在到底在不在运行」。**查询必须读原生状态，不能用 JS 内存布尔值**（页面重建或进程重启后内存值就丢了）。

**推荐的调用方范式——把「数据上报」和「UI 渲染」拆成两个回调**：

- 上报回调由 **App 层**持有（后台持续期间一直执行）
- 渲染回调由 **页面**持有（`onUnmounted` 只解绑它）

很多项目写得别扭，根因就是把这两件事混在一个回调里：页面卸载时不敢解绑（怕丢数据），只好连能力一起停掉。拆开之后，页面卸载只是"不再刷新列表"，能力继续跑。

**启动函数的实现顺序**：

```
① 幂等清理（停旧的 / 解绑旧回调）
② 就绪检查 + 引导（用户可能点「暂不」→ 这里直接抛错返回）
③ 注册回调 + 真正启动
```

把 ② 放在 ③ 之前，避免出现「已注册回调但没启动」的中间态；启动失败也要回滚 ③ 已注册的回调。

**最后一条硬约束**：Android 12+ 禁止后台应用启动前台服务。「到点自动开始」这类需求，正确做法是在**用户进入 App 时**启动并保持，而不是指望后台定时唤醒。

---

## 六、API 设计规范（对齐 uni 原生）

- 单次能力强同步回调三段式：`{ success, fail, complete }`；
- 持续能力强 `onXxxChange(cb)` / `offXxxChange(cb?)` / `startXxxUpdate()` / `stopXxxUpdate()`；
- 🔴 **必须有独立的运行期错误通道** `onXxxError(cb)` / `offXxxError(cb?)`：`startXxxUpdate` 的 `success` 只代表「已启动」，启动之后的异常（权限被撤销、前台服务被系统回收、定位中断）**没有任何出口**。只在「回调列表为空时」透出错误不够——真实业务一定注册了数据回调，错误会被彻底吞掉，表现为「以为在运行、实际早已断流」；
- 🔴 **区分「失败」与「能力降级」两种语义**：能力降级（如后台权限不足但前台定位已成功启动）不应该调用 `fail`，否则调用方看到「先失败后成功」的矛盾顺序。做法：降级原因先存局部变量，等 `success` 抛出之后再通过**只投递给错误监听、不触发 fail** 的 `notifyError()` 抛出；
- 错误对象：`{ errCode: 联合字面量, errSubject: '插件id', errMsg }`，把两端原始错误码收敛成一套；错误码要预留「能力受限」类；
- 结果字段优先对齐 uni 同名 API（如 `uni.getLocation` 的 latitude/longitude/accuracy/altitude/speed/heading/timestamp），扩展字段附加在后；
- 状态查询接口返回布尔能力位（如 `backgroundGranted` / `batteryOptimizationIgnored` / `updating`），让业务层能判断「是否需要引导用户去设置」——权限被永久拒绝后重新申请无效，这比单纯报错更有用；
- 单次与持续能力互斥，用模块级状态变量做状态机；
- 🔴 **参数在各端语义必须一致**：若某参数在某端无原生对应项，要么插件层补齐，要么在类型注释里写明「仅 X 端生效」。静默忽略是最糟的选择——同一份代码两端行为不同且无从排查；
- 🔴 **`offXxxChange(cb)` 按引用相等移除回调，内联箭头函数一定解绑不掉**：

```ts
onXxxChange((res) => list.push(res))     // ✗ 两次创建的是不同函数对象
offXxxChange((res) => list.push(res))    // 摘除失败 → 回调残留在已销毁的页面上
```

后果隐蔽：页面已销毁仍在执行，表现为「进几次该页面后开始卡 / 报错」。两种解法：① 用命名函数；② 更稳的做法是封装层提供「作用域安全」的注册函数，内部固定引用并**返回解绑函数**：

```ts
export function attachXxxListener(cb: (res: any) => void): () => void {
  onXxxChange(cb)
  return () => offXxxChange(cb)      // 闭包捕获同一引用，必然能摘除
}
```

---

## 七、旧原生插件（aar / framework）迁移为 UTS 插件

### 7.1 契约还原：先反编译，再动手

用户最常见的诉求是「调用方式和返回方式跟旧插件保持一致」。一致性不是猜出来的，是**反编译还原出来的**：

- **Android aar**：`unzip xxx.aar` 取 `classes.jar` → `javap -p -classpath cls com.xxx.YourModule` 看方法签名；`javap -c -p` 看字节码还原**错误码常量值、成功回调字段、参数到原生枚举的映射**（常量池字符串会暴露 `"error"`/`"success"`/`"path"` 等 JSON 字段名与 `JSONObject.put` 调用序列）；
- **iOS framework**：`nm -gU` 看 ObjC 符号——类名、IVar（`_useFrontCamera`、`_imagePicker`）、遵循的协议（`UIImagePickerControllerDelegate`）一眼定位实现方式。

必须还原的**隐性契约**（最容易漏）：

- 回调数据形态：JSON **字符串**（`JSON.stringify` 后回调）还是对象？业务侧 `typeof data == 'string'` 分支会暴露真相；
- 用户取消拍照 / 选择时**是否回调**（很多旧插件取消是静默的，新插件必须保持一致）；
- 文件路径是否带 `file://` 前缀；
- 错误码数值表（10001/10002/10003…各对应什么）。

**调用方业务代码的回调体一行都不要动**，只替换插件获取方式。

### 7.2 调用点按「插件名 + 方法名」全局扫所有文件类型

```
grep -rn "插件名\|方法名" --include="*.vue" --include="*.js" --include="*.ts" --include="*.uts" --include="*.nvue" 全项目
```

🔴 范围是**全项目**，不是只搜 `requireNativePlugin` + pages 目录——**三方组件藏在 uni_modules 里**（实战踩坑：上传组件 `uni_modules/cc-imgPreDelUpload` 内部也调了原生相机插件，漏改 = 运行时 `requireNativePlugin` 返回 undefined → `Cannot read property 'openFrontCamera' of undefined`）。改完再扫一遍确认 0 残留，`requireNativePlugin('旧插件名')` 和 `旧实例.方法名` 两个模式都要扫。

### 7.3 Manifest 合并：资源能搬，authority 唯一

- UTS 插件的 `app-android/AndroidManifest.xml` 会合并进主工程：权限、`<queries>`（Android 11+ 包可见性，`resolveActivity` 系统相机必需）、`<provider>` 都可以声明；`res/xml/` 资源文件随插件合并；
- 🔴 **FileProvider authority 全局唯一**：新旧插件并存、都声明 `${applicationId}.fileprovider` → Manifest Merge 冲突，**云打包必失败**。迁移完成后必须从 `manifest.json` 的 `plugins` + `nativePlugins` 两处移除旧插件注册；
- `resolveActivity` 在 Android 11+ 受包可见性限制，插件 manifest 里加 `<queries><intent><action android:name="android.media.action.IMAGE_CAPTURE"/></intent></queries>` 双保险。

### 7.4 Activity 结果回传类插件的范式（onAppActivityResult）

**适用范围不限于拍照 / 选图**：凡通过 `startActivityForResult` 拉起外部 Activity 并把结果回传 JS 的场景都走这套范式——系统相机 / 相册、SAF 文件选择、三方授权登录（微信 / QQ）、支付结果页、地图 POI 选点、人脸识别 / OCR 拍摄 SDK、系统设置页返回。共同结构：**发起时拿到 JS callback → `startActivityForResult` → 异步结果 → 靠模块级 pendingCallback 桥回 JS**。

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
      cb(JSON.stringify({ success: true, path: finalPath }))
    } else {
      // 用户取消（跟原契约：不回调）
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

🔴 **回调体里每一步都要打日志**（收到的原始 requestCode/resultCode、压缩前后路径、回调是否发出）。「JS 调用了但没回调」的排查三板斧：① 确认手机跑的是新 JS（业务侧加打印）② 确认运行时选的是含插件的**自定义基座** ③ 在 UTS 回调链每一环加日志。**回调体里没日志就是排查盲区**。

✅ 真机验证结论（2026-10 实测）：宿主对 `onAppActivityResult` **原样传递 requestCode**（发 1101 收 1101）与 resultCode（拍照确认收 -1）；`requestSystemPermission` 已授权场景直接同步回调 allRight=true；系统相机 `ACTION_IMAGE_CAPTURE` + `EXTRA_OUTPUT(FileProvider)` + maxWidth 压缩 + JSON 字符串回调全链路可用。

---

## 八、编译运行与调试

**核心心智模型**：`index.uts` 在编译期被转成 Kotlin / Swift 编进基座包，运行时读的是基座里那份。

> 🔴 **改了 `utssdk/app-*/index.uts` 任何一行原生代码 → 必须重做自定义基座。只改 JS / 页面代码不用重做。**

流程：`运行 → 运行到手机或模拟器 → 制作自定义调试基座`（选平台、勾原生插件、云端打包 5~15 分钟，iOS 更久因为要 pod install）→ 打包完成后再 `运行到 Android/iOS App 基座`，选「自定义基座」。

其他要点：

- CLI（vue-cli / Vite）项目也要用 HBuilderX「打开目录」来跑，UTS 原生编译链路依赖 HBuilderX；
- 调试技巧：给 `utssdk/index.uts` 写一套委托 `uni.getXxx` 的兜底实现，就能在 H5 端先调 UI 逻辑，不用每次等基座；
- 建议同时写一份 `docs/USAGE.md` 操作手册，把「改了代码要不要重做基座」「Key 的包名+SHA1 绑定」「后台定位 6 项检查」这类高频问题前置说明；
- **第三方 Key 类 SDK 的通用坑**：Android Key 校验「包名 + 签名 SHA1」组合，调试证书与发布证书 SHA1 不同 → 出现"调试能定位、正式包定位失败"。README/USAGE 里要提醒为同一包名配两把 Key 或统一用同一证书；
- 隐私合规接口（updatePrivacyShow / updatePrivacyAgree）与 apiKey 都必须在 SDK 实例化**之前**调用，顺序错了静默失效；
- 遇到 `Project with path ':uni_modules:xxx' could not be found` 先别急着查那个模块——**多半是另一个 UTS 插件编译失败的连带现象**（编译中断导致该模块的 Gradle 子工程没生成）。往上翻日志找第一个 `compileReleaseKotlin` 失败才是真正根因。

---

## 九、交付自检清单

插件交付前逐项核对（本轮实战验证有效）：

**数字类型（云打包才炸，静态看不出来）**

- [ ] 源码里没有 `Number(` 误用（应为 `Number.from(`）
- [ ] 没有 `number` 变量直传原生数字参数（应走 `toInt()/toLong()/toDouble()/toFloat()`）
- [ ] 赋给原生 Int 字段 / 重载参数的变量，声明时显式 `: Int`（含三元拆分为 if/else 字面量直传的场景）

**接口与实现一致性**

- [ ] 实现里引用的每个 option 字段都在 `interface.uts` 声明过（UTS 强类型，漏声明编译失败）
- [ ] 模块级状态变量（pendingCallback 等）逐个确认「有声明 + 有读取 + **有写入**」三件套
- [ ] 页面 `onUnmounted` 有 `offXxxChange()` + `stopXxxUpdate()`，且解绑用的是稳定引用（命名函数或 attach 返回的解绑函数）

**权限与后台（能编译 ≠ 能用）**

- [ ] Android 权限按「前台定位 → POST_NOTIFICATIONS → 后台定位」递增申请，每批独占
- [ ] `enableBackgroundLocation` 包了 try/catch（Android 12+ 后台启动前台服务会抛异常）
- [ ] iOS 实现了 `doRequireLocationAuth`，`allowsBackgroundLocationUpdates` 先设后 start / 先 stop 后置 false
- [ ] 走完「未授权 / 已拒绝 / 已被永久拒绝 / 系统总开关关闭 / 省电白名单未放行」五种初始状态，每种都能给出**可执行的**引导
- [ ] 权限弹窗是否出现 / 系统设置里能否看到权限项 / 熄屏后是否仍有回调——三步实测

**迁移专项**

- [ ] 「插件名 + 方法名」全项目扫描 0 残留（含 uni_modules 深处的三方组件）
- [ ] `manifest.json` 的 `plugins` + `nativePlugins` 两处都移除了旧插件注册
- [ ] FileProvider authority 无双声明（Manifest Merge 冲突云打包必败）

**文档**

- [ ] README 里显式列出「依赖原生类名 / 签名的互操作点」及替代方案（排查成本远低于让使用者自己猜）
- [ ] iOS delegate 签名、泛型字典类型等**无法本地验证**的点，显式列为「真机验证清单」
- [ ] 不把操作系统层面无法保证的（如 App 被强杀后自动恢复定位）写成承诺，并提供「断流可感知」的错误通道作为方案的一环

---

## 十、高频踩坑速查（完整 22 条见 SKILL.md）

| # | 坑 | 一句话对策 |
|---|---|---|
| 1 | 文档正文的 SDK 版本号滞后 / 自相矛盾 | 以 Maven metadata / pod 页为准 |
| 2 | iOS `@argumentLabel` 写错 → 代理永远不回调且不报错 | 每个参数都显式标注，真机验证 |
| 4 | 隐私合规接口与 apiKey 顺序错了静默失效 | 都在 SDK 实例化**之前**调用 |
| 7 | 实现引用 interface 未声明字段 → 编译失败 | 改原生 SDK 前先 grep 接口文件 |
| 8 | 「能编译」≠「能用」 | 权限类功能按三步实测 |
| 9 | 强杀后自动恢复定位无法保证 | 明确告知边界 + 断流可感知 |
| 11 | 把「返回错误码」当成「做好了权限处理」 | 提供体检 + 分场景跳转 |
| 13 | `Number(x)` / number 直传原生参数 | 云打包才炸，「进 from 出 toXXX」 |
| 14 | `could not be found` 连带现象 | 往上翻找第一个 compileReleaseKotlin 失败 |
| 15 | `offXxxChange` 内联箭头解绑不掉 | 命名函数或 attach 返回解绑函数 |
| 17 | iOS 标签用 `:` / trailing closure | 一律 `=` + 具名参数 |
| 18 | 数字字面量推断为 number 赋给 Int | 显式 `: Int` 或 if/else 字面量直传 |
| 19 | 三方组件藏在 uni_modules 深处漏扫 | 全项目扫所有文件类型 |
| 20 | FileProvider authority 双声明 | 云打包必败，迁移后移除旧插件注册 |
| 21 | 「JS 调了但没回调」 | 三板斧：新 JS → 自定义基座 → 每环打日志 |
| 22 | pendingCallback 声明了、读了、忘赋值 | 每个被读取的模块级状态变量确认有写入点 |
