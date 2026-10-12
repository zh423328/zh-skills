/**
 * 将 app 平台构建产物（dist/build/app-plus）压缩为 wgt 包
 * 用法：node scripts/pack-wgt.js  （通常通过 pnpm build:wgt 调用）
 * 产物：dist/release/${appid}_${versionCode}.wgt（命名规则同官方文档 quickstart-cli）
 *
 * wgt 本质是 zip：根目录必须包含 manifest.json，因此必须先执行 uni build -p app
 */
const { execSync } = require('node:child_process')
const fs = require('node:fs')
const path = require('node:path')

const root = path.resolve(__dirname, '..')
const srcDir = path.join(root, 'dist/build/app-plus')
const outDir = path.join(root, 'dist/release')

if (!fs.existsSync(path.join(srcDir, 'manifest.json'))) {
  console.error('未找到 dist/build/app-plus/manifest.json，请先执行 uni build -p app')
  process.exit(1)
}

// manifest.json 允许注释（JSONC），不能用 JSON.parse，改用正则直接提取所需字段
const raw = fs.readFileSync(path.join(root, 'src/manifest.json'), 'utf8')
const versionCode = (raw.match(/"versionCode"\s*:\s*(\d+)/) || [])[1]
const appid = (raw.match(/"appid"\s*:\s*"([^"]+)"/) || [])[1]
if (!versionCode || !appid) {
  console.error('src/manifest.json 缺少 versionCode / appid，请检查配置')
  process.exit(1)
}

fs.mkdirSync(outDir, { recursive: true })
// 命名规则参考官方文档 quickstart-cli：${appid}_${versionCode}.wgt
const outFile = path.join(outDir, `${appid}_${versionCode}.wgt`)

// zip 根目录必须是 manifest.json 所在层级，所以用 (cd srcDir && zip .) 而不是 zip srcDir
execSync(`rm -f "${outFile}" && cd "${srcDir}" && zip -qr "${outFile}" .`, { stdio: 'inherit' })

const size = (fs.statSync(outFile).size / 1024 / 1024).toFixed(2)
console.log(`WGT 打包完成: ${outFile} (${size} MB)`)
console.log('发版提醒: versionCode=' + versionCode + ' 需大于线上资源版本，并在服务端版本接口同步递增')
