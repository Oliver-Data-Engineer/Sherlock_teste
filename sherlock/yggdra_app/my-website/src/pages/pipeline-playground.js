import React from 'react';
import Layout from '@theme/Layout';
import PipelinePlayground from '@site/src/components/PipelinePlayground';

export default function PipelinePlaygroundPage() {
  return (
    <Layout title="Testar configuração da pipeline" description="Monte, valide e baixe o YAML de configuração da pipeline.">
      <main className="container container--fluid margin-vert--lg" style={{maxWidth: 1440}}>
        <PipelinePlayground />
      </main>
    </Layout>
  );
}
