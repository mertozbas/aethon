import clsx from 'clsx';
import Heading from '@theme/Heading';
import Translate from '@docusaurus/Translate';

const FeatureList = [
  {
    icon: '🔌',
    title: <Translate id="feat.byop.title">Bring your own provider</Translate>,
    body: (
      <Translate id="feat.byop.body">
        Defaults to OpenAI, or point it at any OpenAI-compatible endpoint
        (vLLM, LM Studio, LocalAI), the Anthropic API, a fully-local Ollama
        model — plus Bedrock, Gemini, LiteLLM, and Mistral. Flip one line of config.
      </Translate>
    ),
  },
  {
    icon: '💬',
    title: <Translate id="feat.channels.title">Every channel, one package</Translate>,
    body: (
      <Translate id="feat.channels.body">
        Terminal CLI, a browser WebChat UI, and Telegram / Discord / Slack bots
        (WhatsApp experimental) — all shipped in a single install, talking to one
        persistent assistant.
      </Translate>
    ),
  },
  {
    icon: '🧠',
    title: <Translate id="feat.memory.title">Memory & specialists</Translate>,
    body: (
      <Translate id="feat.memory.body">
        Long-term SQLite vector memory, plus Coder / Researcher / Analyst / Planner
        sub-agents the orchestrator delegates to. It remembers what matters and
        farms out the hard parts.
      </Translate>
    ),
  },
  {
    icon: '⚙️',
    title: <Translate id="feat.sops.title">SOPs & scheduler</Translate>,
    body: (
      <Translate id="feat.sops.body">
        Reusable slash-invoked workflows (SOPs) plus a cron scheduler that runs
        them on a timetable and delivers results to any channel.
      </Translate>
    ),
  },
  {
    icon: '📊',
    title: <Translate id="feat.dashboard.title">Live dashboard</Translate>,
    body: (
      <Translate id="feat.dashboard.body">
        Watch sessions, memory, telemetry, agents, and SOPs in real time —
        with session recording and replay, and a pixel-agent "live company" view.
      </Translate>
    ),
  },
  {
    icon: '🔒',
    title: <Translate id="feat.local.title">Local-first & private</Translate>,
    body: (
      <Translate id="feat.local.body">
        Services bind to 127.0.0.1 by default and your data lives under ~/.aethon.
        Workspace sandbox, blocked-command filtering, approval hooks, and a memory
        guard keep you in control.
      </Translate>
    ),
  },
];

function Feature({icon, title, body}) {
  return (
    <div className={clsx('col col--4')} style={{marginBottom: '1.5rem'}}>
      <div className="featureCard">
        <span className="featureIcon">{icon}</span>
        <Heading as="h3">{title}</Heading>
        <p>{body}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures() {
  return (
    <section className="featureSection">
      <div className="container">
        <Heading as="h2" className="sectionTitle">
          <Translate id="feat.section.title">One assistant, fully yours</Translate>
        </Heading>
        <p className="sectionLead">
          <Translate id="feat.section.lead">
            AETHON is a single Python package that gives one memory-backed assistant
            every entry point you need — and never takes your data or your model
            choice out of your hands.
          </Translate>
        </p>
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
