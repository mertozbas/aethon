import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Translate, {translate} from '@docusaurus/Translate';
import CodeBlock from '@theme/CodeBlock';

import HomepageFeatures from '@site/src/components/HomepageFeatures';

function Hero() {
  return (
    <header className="hero--aethon">
      <div className="container">
        <h1 className="hero__title">AETHON</h1>
        <p className="hero__subtitle">
          <Translate id="home.hero.subtitle">
            A self-hosted, provider-agnostic personal AI assistant — Web UI, CLI,
            and messaging bots, with memory, multi-agent specialists, SOPs, a
            scheduler, telemetry, and a live dashboard. You run it; you choose the
            backend.
          </Translate>
        </p>

        <div className="heroBadges">
          <img src="https://img.shields.io/pypi/v/aethon-ai.svg" alt="PyPI" />
          <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg" alt="Python" />
          <img src="https://img.shields.io/badge/license-PolyForm--Noncommercial--1.0.0-orange.svg" alt="License" />
          <img src="https://img.shields.io/badge/built%20with-Strands%20Agents%20SDK-7d4cdb.svg" alt="Strands" />
        </div>

        <div className="heroButtons">
          <Link className="button button--primary button--lg" to="/docs/intro">
            <Translate id="home.hero.read">Read the Handbook</Translate>
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/docs/getting-started/installation">
            <Translate id="home.hero.install">Install in 3 commands</Translate>
          </Link>
        </div>

        <div style={{maxWidth: 560, margin: '2.25rem auto 0', textAlign: 'left'}}>
          <CodeBlock language="bash">{`pip install aethon-ai
aethon init      # pick a provider, paste a key (or go local)
aethon start     # → http://127.0.0.1:18790`}</CodeBlock>
        </div>
      </div>
    </header>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={translate({
        id: 'home.meta.title',
        message: 'AETHON — Personal AI assistant you run yourself',
      })}
      description={siteConfig.tagline}>
      <Hero />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
