---
import BaseLayout from '../layouts/BaseLayout.astro';
import { SITE_NAME } from '../lib/site';
---

<BaseLayout title={SITE_NAME} description="Website of {{title}}. Replace this text with one real sentence of 120 to 160 characters that says what visitors find here." current="home">
  <div class="container">
    <header class="page-header">
      <h1 class="page-header__title">{SITE_NAME}</h1>
      {{lead_line}}
    </header>
  </div>
</BaseLayout>
