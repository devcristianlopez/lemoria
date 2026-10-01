import { execFileSync } from "node:child_process"
import { existsSync, rmSync, unlinkSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { homedir } from "node:os"

const HOME = homedir()
const CONFIG = join(HOME, ".config", "opencode")
const GLOBAL_AGENTS_DIR = join(CONFIG, "agents")
const AGENTS = [
  "orchestrator",
  "implementation-agent",
  "frontend-agent",
  "db-agent",
  "testing-agent",
  "review-agent",
  "github-agent",
  "documentation-agent",
]
const EFFORTS = [
  { title: "Default", value: "" },
  { title: "Low", value: "low" },
  { title: "Medium", value: "medium" },
  { title: "High", value: "high" },
]
const FALLBACK_MODELS = [
  { title: "openai/gpt-5.5", value: "openai/gpt-5.5", variants: ["none", "low", "medium", "high"] },
]
let CURRENT_SESSION_ID = undefined

// ----- Where Lemoria lives on this machine -----
// install.sh writes config.json next to tui.js; the env vars are the manual
// escape hatches. Nothing here may assume ~/Projects/lemoria exists.

function pluginDir() {
  try {
    return dirname(new URL(import.meta.url).pathname)
  } catch {
    return undefined
  }
}

function readSettings() {
  const dir = pluginDir()
  if (!dir) return {}
  try {
    return JSON.parse(readFileSync(join(dir, "config.json"), "utf8")) || {}
  } catch {
    return {}
  }
}

const SETTINGS = readSettings()
const REPO = SETTINGS.repo || process.env.LEMORIA_REPO || undefined

function resolveAgentsDir() {
  const candidates = [
    SETTINGS.agentsDir,
    process.env.LEMORIA_OPENCODE_AGENTS_DIR,
    REPO && join(REPO, ".opencode", "agents"),
    GLOBAL_AGENTS_DIR,
    join(process.cwd(), ".opencode", "agents"),
  ].filter(Boolean)
  return candidates.find((candidate) => existsSync(candidate))
}

const AGENTS_DIR = resolveAgentsDir()

function short(text, max = 900) {
  const value = String(text || "").trim()
  if (value.length <= max) return value || "OK"
  return `${value.slice(0, max)}\n…`
}

function run(bin, args, options = {}) {
  return execFileSync(bin, args, {
    encoding: "utf8",
    stderr: "pipe",
    maxBuffer: 1024 * 1024,
    ...options,
  }).trim()
}

// `lemoria agent ...` writes the pin into settings.opencode_agents_dir, which
// defaults to ./.opencode/agents. Point it at the directory the installer used
// so the menu works from any project, not only from the Lemoria checkout.
function runLemoria(args) {
  const env = { ...process.env }
  if (AGENTS_DIR) env.LEMORIA_OPENCODE_AGENTS_DIR = AGENTS_DIR
  return run("lemoria", args, { env }) || "OK"
}

function runOpenCodeApi(args) {
  return run("opencode", ["api", ...args], { cwd: REPO })
}

function reloadOpenCode() {
  try { return run("opencode", ["reload"]) || "recargado" }
  catch (error) { return `reload falló: ${error.stderr?.toString?.() || error.message || String(error)}` }
}

function parseModelRef(model, effort) {
  const [withoutVariant, embeddedVariant] = String(model).split("#")
  const slash = withoutVariant.indexOf("/")
  if (slash < 1) return null
  const providerID = withoutVariant.slice(0, slash)
  const id = withoutVariant.slice(slash + 1)
  const variant = effort || embeddedVariant || undefined
  return variant ? { providerID, id, variant } : { providerID, id }
}

function activeSessionIDs(context) {
  if (CURRENT_SESSION_ID) return [CURRENT_SESSION_ID]
  const routerCurrent = context?.ui?.router?.current?.()
  if (routerCurrent?.type === "session" && routerCurrent.sessionID) return [routerCurrent.sessionID]
  const current = context?.route?.current
  if (current?.name === "session" && current.params?.sessionID) return [current.params.sessionID]
  try {
    const data = JSON.parse(runOpenCodeApi(["session.active"]))?.data || {}
    const ids = Object.keys(data)
    if (ids.length) return ids
  } catch {}
  try {
    const params = REPO ? ["--param", `directory=${REPO}`] : []
    const list = JSON.parse(runOpenCodeApi(["session.list", "--param", "limit=1", ...params]))?.data || []
    if (list[0]?.id) return [list[0].id]
  } catch {}
  return []
}

// The TUI label next to the prompt shows the session model, so the pin alone
// is not enough: mirror it into the session the user is looking at.
function switchActiveSessions(context, agent, model, effort) {
  const ref = parseModelRef(model, effort)
  if (!ref) return "modelo inválido"
  const sessions = activeSessionIDs(context)
  for (const sessionID of sessions) {
    try { runOpenCodeApi(["session.switchAgent", "--param", `sessionID=${sessionID}`, "-d", JSON.stringify({ agent })]) } catch {}
    try { runOpenCodeApi(["session.switchModel", "--param", `sessionID=${sessionID}`, "-d", JSON.stringify({ model: ref })]) } catch {}
  }
  return sessions.length ? `pantalla actualizada (${sessions.length})` : "sin sesión activa"
}

function updateLemoriaSlashCommand(model, effort) {
  const file = join(CONFIG, "commands", "lemoria.md")
  if (!existsSync(file)) return
  let text = readFileSync(file, "utf8")
  const modelValue = effort ? `${String(model).split("#")[0]}#${effort}` : String(model)
  text = text.replace(/^agent:.*$/m, "agent: orchestrator")
  text = text.replace(/^model:.*$/m, `model: ${modelValue}`)
  writeFileSyncSafe(file, text)
}

function writeFileSyncSafe(file, text) {
  try {
    writeFileSync(file, text)
  } catch {}
}

function toast(context, input) {
  const fn = context.ui?.toast?.show ?? context.ui?.toast
  if (typeof fn === "function") fn(input)
}

async function alert(context, title, message) {
  const body = short(message)
  if (typeof context.ui?.dialog?.alert === "function") {
    await context.ui.dialog.alert({ title, message: body })
    return
  }
  toast(context, { variant: "info", title, message: body, duration: 5000 })
}

async function select(context, title, options) {
  if (typeof context.ui?.dialog?.select !== "function") {
    await alert(context, title, "Tu versión de OpenCode no expone select dialogs.")
    return undefined
  }
  const result = await context.ui.dialog.select({ title, options })
  return result?.value ?? result
}

async function confirm(context, title, message) {
  if (typeof context.ui?.dialog?.confirm === "function") {
    return await context.ui.dialog.confirm({
      title,
      message,
      label: { confirm: "Sí", cancel: "Cancelar" },
    })
  }
  return (await select(context, title, [
    { title: "Cancelar", value: false },
    { title: "Sí", value: true },
  ])) === true
}

async function showCommand(context, title, args, options = {}) {
  try {
    const output = runLemoria(args)
    const reload = options.reload ? `\n${reloadOpenCode()}` : ""
    await alert(context, title, `${output}${reload}`)
  } catch (error) {
    await alert(context, `${title} falló`, `${error.stderr?.toString?.() || error.message || String(error)}\nAgentes: ${AGENTS_DIR || "no encontrado"}`)
  }
}

async function chooseAgent(context, title = "Agente") {
  return await select(context, title, AGENTS.map((agent) => ({ title: agent, value: agent })))
}

// Only models the user's account can actually reach: opencode disables the
// rest, so we never offer them. No provider is hardcoded here.
function modelsFromOpencode() {
  try {
    const data = JSON.parse(run("opencode", ["api", "model.list"]))?.data || []
    const models = data
      .filter((model) => model.enabled !== false && model.id && model.providerID)
      .map((model) => ({
        title: `${model.providerID}/${model.id}`,
        value: `${model.providerID}/${model.id}`,
        variants: (model.variants || []).map((variant) => variant.id).filter(Boolean),
      }))
    if (models.length) return models.slice(0, 60)
    return FALLBACK_MODELS
  } catch {
    return FALLBACK_MODELS
  }
}

async function chooseModel(context) {
  return await select(context, "Modelo", modelsFromOpencode())
}

function variantsForModel(model) {
  return modelsFromOpencode().find((entry) => entry.value === model)?.variants || []
}

async function chooseEffort(context, title = "Esfuerzo", model = undefined) {
  const variants = model ? variantsForModel(model) : []
  const options = variants.length
    ? variants.map((variant) => ({ title: variant === "none" ? "Default" : variant, value: variant === "none" ? "" : variant }))
    : EFFORTS
  return await select(context, title, options)
}

// One command does the whole job: agent -> model -> effort. The pin goes to a
// single directory (the one the installer configured), so the user's own git
// repositories never get dirty, and opencode reload picks it up.
async function setAgentModel(context) {
  const agent = await chooseAgent(context, "Modelo: agente")
  if (!agent) return
  const model = await chooseModel(context)
  if (!model) return
  const effort = await chooseEffort(context, "Esfuerzo opcional", model)
  const args = ["agent", "model", agent, model]
  if (effort) args.push("--effort", effort)
  try {
    const output = runLemoria(args)
    if (agent === "orchestrator") updateLemoriaSlashCommand(model, effort)
    const reload = reloadOpenCode()
    const screen = switchActiveSessions(context, agent, model, effort)
    await alert(context, "Agente configurado", `${agent} ${effort ? `#${effort}` : ""}
${output}
${screen}
${reload}`)
  } catch (error) {
    await alert(context, "Modelo falló", `${error.stderr?.toString?.() || error.message || String(error)}
Agentes: ${AGENTS_DIR || "no encontrado"}`)
  }
}

async function clearAgentModel(context) {
  const agent = await chooseAgent(context, "Limpiar modelo")
  if (!agent) return
  try {
    const output = runLemoria(["agent", "model", agent, "--clear"])
    const reload = reloadOpenCode()
    await alert(context, "Modelo limpiado", `${output}
${reload}`)
  } catch (error) {
    await alert(context, "Limpiar falló", `${error.stderr?.toString?.() || error.message || String(error)}`)
  }
}

async function clearAgentEffort(context) {
  const agent = await chooseAgent(context, "Limpiar esfuerzo")
  if (!agent) return
  try {
    const output = runLemoria(["agent", "effort", agent, "--clear"])
    const reload = reloadOpenCode()
    await alert(context, "Esfuerzo limpiado", `${output}
${reload}`)
  } catch (error) {
    await alert(context, "Limpiar falló", `${error.stderr?.toString?.() || error.message || String(error)}`)
  }
}

function removePath(path) {
  try {
    if (existsSync(path)) rmSync(path, { recursive: true, force: true })
  } catch {}
}

function removeFile(path) {
  try {
    if (existsSync(path)) unlinkSync(path)
  } catch {}
}

function removeCliPluginEntry() {
  const cli = join(CONFIG, "cli.json")
  if (!existsSync(cli)) return
  try {
    const data = JSON.parse(readFileSync(cli, "utf8"))
    if (Array.isArray(data.plugins)) {
      data.plugins = data.plugins.filter((entry) => !String(entry).includes("lemoria-menu"))
      writeFileSyncSafe(cli, `${JSON.stringify(data, null, 2)}\n`)
    }
  } catch {}
}

async function uninstallLemoria(context) {
  const mode = await select(context, "Desinstalar Lemoria", [
    { title: "Cancelar", value: "cancel" },
    { title: "Solo integraciones OpenCode", value: "ui" },
    { title: "Completo", value: "full" },
  ])
  if (!mode || mode === "cancel") return
  const ok = await confirm(context, "Confirmar", mode === "full"
    ? "Quita menú, agentes, skills, comandos, CLI, DB local y vault."
    : "Quita menú, agentes, skills y comandos de OpenCode.")
  if (!ok) return

  const steps = []
  try { run("lemoria", ["omarchy", "uninstall"]); steps.push("Omarchy") } catch {}

  for (const agent of AGENTS) removeFile(join(CONFIG, "agents", `${agent}.md`))
  removePath(join(CONFIG, "skills", "lemoria"))
  for (const skill of ["frontend", "backend", "database", "testing", "code-review", "git-workflow", "documentation"]) {
    removePath(join(CONFIG, "skills", skill))
  }
  removeFile(join(CONFIG, "commands", "lemoria.md"))
  steps.push("OpenCode")

  if (mode === "full") {
    removeFile(join(HOME, ".local", "bin", "lemoria"))
    removePath(join(HOME, ".local", "share", "lemoria"))
    removePath(join(HOME, ".lemoria"))
    steps.push("CLI/DB/vault")
  }

  removeCliPluginEntry()
  removePath(join(CONFIG, "plugins", "lemoria-menu"))
  await alert(context, "Desinstalado", `Hecho: ${steps.join(", ")}
Reinicia OpenCode.`)
}

const COMMANDS = [
  { id: "lemoria.menu.start", title: "Lemoria", description: "Abrir flujo SDD", run: (context) => alert(context, "Lemoria", "Usa /lemoria <solicitud> en el prompt.") },
  { id: "lemoria.agent.status", title: "Lemoria: agentes", description: "Estado", run: (context) => showCommand(context, "Agentes", ["agent", "status"]) },
  { id: "lemoria.agent.set_model", title: "Lemoria: modelo", description: "Agente + modelo + esfuerzo", run: setAgentModel },
  { id: "lemoria.agent.clear_model", title: "Lemoria: limpiar modelo", description: "Quitar pin", run: clearAgentModel },
  { id: "lemoria.agent.clear_effort", title: "Lemoria: limpiar esfuerzo", description: "Quitar esfuerzo", run: clearAgentEffort },
  { id: "lemoria.agent.sync", title: "Lemoria: sync", description: "Sincronizar agentes", run: (context) => showCommand(context, "Sync", ["agent", "sync"], { reload: true }) },
  { id: "lemoria.uninstall", title: "Lemoria: desinstalar", description: "Quitar Lemoria", run: uninstallLemoria },
]

function registerLemoriaCommands(context) {
  return context.keymap.layer(() => ({
    mode: "global",
    priority: 20,
    commands: COMMANDS.map((command) => ({
      id: command.id,
      title: command.title,
      description: command.description,
      group: "Lemoria",
      palette: true,
      suggested: false,
      slash: command.id === "lemoria.menu.start" ? { name: "lemoria", aliases: ["sdd"], arguments: true } : undefined,
      enabled: () => true,
      run: (input) => command.run(context, input),
    })),
    bindings: [],
  }))
}

export default {
  id: "lemoria.menu",
  setup(context) {
    const disposeApp = context.ui.slot({
      append: "app",
      render: () => {
        registerLemoriaCommands(context)
        return null
      },
    })
    const disposeSession = context.ui.slot({
      append: "session_prompt_right",
      render: (props) => {
        CURRENT_SESSION_ID = props?.session_id
        return null
      },
    })
    return () => {
      if (typeof disposeApp === "function") disposeApp()
      if (typeof disposeSession === "function") disposeSession()
    }
  },
}
