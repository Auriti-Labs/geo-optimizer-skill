#!/usr/bin/env python3
"""
Schema Injector — Aggiunge schema JSON-LD a pagine HTML e componenti Astro
Generative Engine Optimization (GEO) Skill

Autore: Juan Auriti (juancamilo.auriti@gmail.com)
Skill: geo-optimizer (OpenClaw)

Uso:
    # Analizza file HTML e mostra schema suggerito
    python schema_injector.py --file index.html

    # Inietta schema WebSite in un file HTML
    python schema_injector.py --file index.html --type website --name "MioSito" --url https://example.com

    # Inietta schema FAQPage
    python schema_injector.py --file page.html --type faq --faq-file faqs.json

    # Genera snippet Astro per BaseLayout
    python schema_injector.py --type website --name "CalcFast" --url https://calcfast.online --astro
"""

import argparse
import json
import re
import sys
from pathlib import Path


SCHEMA_TEMPLATES = {
    "website": {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "{{name}}",
        "url": "{{url}}",
        "description": "{{description}}",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": "{{url}}/search?q={search_term_string}"
            },
            "query-input": "required name=search_term_string"
        }
    },
    "webapp": {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": "{{name}}",
        "url": "{{url}}",
        "description": "{{description}}",
        "applicationCategory": "UtilityApplication",
        "operatingSystem": "Web",
        "browserRequirements": "Requires JavaScript",
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD"
        },
        "author": {
            "@type": "Organization",
            "name": "{{author}}"
        }
    },
    "faq": {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": "{{question}}",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "{{answer}}"
                }
            }
        ]
    },
    "article": {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "{{title}}",
        "description": "{{description}}",
        "url": "{{url}}",
        "datePublished": "{{date_published}}",
        "dateModified": "{{date_modified}}",
        "author": {
            "@type": "Person",
            "name": "{{author}}"
        },
        "publisher": {
            "@type": "Organization",
            "name": "{{publisher}}",
            "logo": {
                "@type": "ImageObject",
                "url": "{{logo_url}}"
            }
        }
    },
    "organization": {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "{{name}}",
        "url": "{{url}}",
        "description": "{{description}}",
        "logo": "{{logo_url}}",
        "sameAs": []
    },
    "breadcrumb": {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "{{url}}"
            }
        ]
    }
}

ASTRO_TEMPLATES = {
    "website": '''---
// Nel BaseLayout.astro o Layout.astro
interface Props {
  title: string;
  description: string;
  url?: string;
  isCalculator?: boolean;
  faqItems?: Array<{ question: string; answer: string }>;
}

const {
  title,
  description,
  url = Astro.url.href,
  isCalculator = false,
  faqItems = [],
} = Astro.props;

const siteUrl = "{site_url}";
const siteName = "{site_name}";

const websiteSchema = {{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": siteName,
  "url": siteUrl,
  "description": description,
  "potentialAction": {{
    "@type": "SearchAction",
    "target": `${{siteUrl}}/search?q={{search_term_string}}`,
    "query-input": "required name=search_term_string"
  }}
}};

const webAppSchema = isCalculator ? {{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": title,
  "url": url,
  "description": description,
  "applicationCategory": "UtilityApplication",
  "operatingSystem": "Web",
  "offers": {{ "@type": "Offer", "price": "0", "priceCurrency": "USD" }}
}} : null;

const faqSchema = faqItems.length > 0 ? {{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": faqItems.map(item => ({{
    "@type": "Question",
    "name": item.question,
    "acceptedAnswer": {{ "@type": "Answer", "text": item.answer }}
  }}))
}} : null;
---

<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{{title}} | {{siteName}}</title>
  <meta name="description" content={{description}} />
  <link rel="canonical" href={{url}} />

  <!-- Open Graph -->
  <meta property="og:title" content={{title}} />
  <meta property="og:description" content={{description}} />
  <meta property="og:url" content={{url}} />
  <meta property="og:type" content="website" />

  <!-- GEO: Schema JSON-LD -->
  <script type="application/ld+json" set:html={{JSON.stringify(websiteSchema)}} />
  {{webAppSchema && <script type="application/ld+json" set:html={{JSON.stringify(webAppSchema)}} />}}
  {{faqSchema && <script type="application/ld+json" set:html={{JSON.stringify(faqSchema)}} />}}
</head>
''',
}


def fill_template(template: dict, values: dict) -> dict:
    """Sostituisce i placeholder nel template con i valori forniti."""
    template_str = json.dumps(template)
    for key, value in values.items():
        template_str = template_str.replace(f"{{{{{key}}}}}", str(value) if value else "")
    return json.loads(template_str)


def schema_to_html_tag(schema_dict: dict) -> str:
    """Converte schema dict in tag HTML script."""
    json_str = json.dumps(schema_dict, indent=2, ensure_ascii=False)
    return f'<script type="application/ld+json">\n{json_str}\n</script>'


def analyze_html_file(file_path: str) -> dict:
    """Analizza un file HTML e suggerisce gli schema mancanti."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("❌ beautifulsoup4 richiesto: pip install beautifulsoup4")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    soup = BeautifulSoup(content, "html.parser")

    found_types = []
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                for item in data:
                    found_types.append(item.get("@type", "?"))
            else:
                found_types.append(data.get("@type", "?"))
        except Exception:
            pass

    missing = []
    if "WebSite" not in found_types:
        missing.append("website")
    if "WebApplication" not in found_types:
        missing.append("webapp")
    if "FAQPage" not in found_types:
        missing.append("faq")

    return {
        "found": found_types,
        "missing": missing,
        "has_head": bool(soup.find("head")),
    }


def inject_schema_into_html(file_path: str, schema_tag: str, backup: bool = True) -> bool:
    """Inietta schema JSON-LD in un file HTML."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Backup
    if backup:
        backup_path = file_path + ".bak"
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"   Backup: {backup_path}")

    # Inserisci prima di </head>
    if "</head>" in content:
        new_content = content.replace("</head>", f"\n  {schema_tag}\n</head>", 1)
    elif "<head>" in content:
        new_content = content.replace("<head>", f"<head>\n  {schema_tag}", 1)
    else:
        print("❌ Tag <head> non trovato nel file")
        return False

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def generate_faq_schema(faq_data) -> dict:
    """Genera schema FAQPage da lista di domande/risposte."""
    if isinstance(faq_data, list):
        items = faq_data
    elif isinstance(faq_data, dict) and "faqs" in faq_data:
        items = faq_data["faqs"]
    else:
        print("❌ Formato FAQ non riconosciuto. Usa: [{question, answer}, ...]")
        sys.exit(1)

    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": []
    }

    for item in items:
        q = item.get("question", item.get("q", ""))
        a = item.get("answer", item.get("a", ""))
        schema["mainEntity"].append({
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": a
            }
        })

    return schema


def main():
    parser = argparse.ArgumentParser(
        description="Inietta schema JSON-LD in pagine HTML o genera snippet Astro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", help="File HTML da analizzare/modificare")
    parser.add_argument("--type", choices=["website", "webapp", "faq", "article", "organization", "breadcrumb"],
                        help="Tipo di schema da generare")
    parser.add_argument("--name", help="Nome del sito/applicazione")
    parser.add_argument("--url", help="URL del sito")
    parser.add_argument("--description", default="", help="Descrizione")
    parser.add_argument("--author", default="", help="Autore")
    parser.add_argument("--logo-url", default="", help="URL del logo")
    parser.add_argument("--faq-file", help="File JSON con FAQ [{question, answer}]")
    parser.add_argument("--astro", action="store_true", help="Genera snippet per Astro")
    parser.add_argument("--inject", action="store_true", help="Inietta direttamente nel file --file")
    parser.add_argument("--no-backup", action="store_true", help="Non creare backup prima di modificare")
    parser.add_argument("--analyze", action="store_true", help="Solo analizza il file, non modifica")

    args = parser.parse_args()

    # Solo analisi
    if args.analyze and args.file:
        print(f"\n🔍 Analisi: {args.file}")
        result = analyze_html_file(args.file)
        print(f"   Schema trovati: {', '.join(result['found']) or 'nessuno'}")
        print(f"   Schema mancanti: {', '.join(result['missing']) or 'nessuno ✅'}")
        if result["missing"]:
            print("\n💡 Aggiungi questi schema:")
            for schema_type in result["missing"]:
                print(f"   python schema_injector.py --file {args.file} --type {schema_type} --url URL --name NAME --inject")
        return

    # Genera snippet Astro
    if args.astro:
        template = ASTRO_TEMPLATES.get("website", "")
        template = template.replace("{site_url}", args.url or "https://example.com")
        template = template.replace("{site_name}", args.name or "SiteName")
        print("\n─── Snippet Astro BaseLayout ───")
        print(template)
        return

    # Genera schema
    if args.type:
        if args.type == "faq":
            if args.faq_file:
                with open(args.faq_file, "r") as f:
                    faq_data = json.load(f)
                schema = generate_faq_schema(faq_data)
            else:
                # Schema FAQ di esempio
                schema = {
                    "@context": "https://schema.org",
                    "@type": "FAQPage",
                    "mainEntity": [
                        {
                            "@type": "Question",
                            "name": "Come funziona questo strumento?",
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": "Inserisci i dati richiesti e ottieni il risultato istantaneamente."
                            }
                        },
                        {
                            "@type": "Question",
                            "name": "Il servizio è gratuito?",
                            "acceptedAnswer": {
                                "@type": "Answer",
                                "text": "Sì, tutti gli strumenti sono completamente gratuiti."
                            }
                        }
                    ]
                }
        else:
            template = SCHEMA_TEMPLATES.get(args.type, {})
            values = {
                "name": args.name or "Nome Sito",
                "url": args.url or "https://example.com",
                "description": args.description or "",
                "author": args.author or "",
                "logo_url": args.logo_url or "",
            }
            schema = fill_template(template, values)

        schema_tag = schema_to_html_tag(schema)

        if args.inject and args.file:
            print(f"\n💉 Inietta {args.type} schema in: {args.file}")
            success = inject_schema_into_html(args.file, schema_tag, backup=not args.no_backup)
            if success:
                print(f"✅ Schema {args.type} iniettato con successo!")
            else:
                print("❌ Iniezione fallita")
        else:
            print(f"\n─── Schema {args.type.upper()} JSON-LD ───")
            print(schema_tag)
            if args.file:
                print(f"\n💡 Per iniettare: aggiungi --inject")

        return

    # Analisi file senza tipo specificato
    if args.file:
        result = analyze_html_file(args.file)
        print(f"\n🔍 Analisi schema in: {args.file}")
        print(f"   ✅ Trovati: {', '.join(result['found']) or 'nessuno'}")
        if result["missing"]:
            print(f"   ❌ Mancanti: {', '.join(result['missing'])}")
            print("\n💡 Comandi suggeriti:")
            for t in result["missing"]:
                print(f"   python schema_injector.py --file {args.file} --type {t} --name 'Nome' --url 'URL' --inject")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
