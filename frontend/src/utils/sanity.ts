import {sanityClient} from 'sanity:client'
import {defineQuery} from 'groq'

export interface SanityArticle {
  _id: string
  title: string
  metaTitle?: string
  slug: {current: string}
  description: string
  category: 'guides' | 'tools' | 'resources' | 'state-of-geo'
  datePublished: string
  dateModified: string
  body: unknown[]
  faqs?: {question: string; answer: string; _key: string}[]
  ogImage?: {asset: {_ref: string}; alt?: string}
  focusKeyword?: string
  llmsContext?: string
  schemaOrgType?: 'Article' | 'TechArticle' | 'HowTo'
  author?: string
  noindex?: boolean
  firstImage?: { asset: { _ref: string }; alt?: string }
}

// Un articolo e' live solo dopo una pubblicazione esplicita. I contenuti legacy
// senza status restano visibili per compatibilita'. Gli articoli programmati sono
// promossi a "published" dal job GitHub prima di avviare il deploy statico.
const LIVE = `(!defined(status) || status == "published")`

const SLUGS_QUERY = defineQuery(
  `*[_type == "article" && defined(slug.current) && ${LIVE}]{ "slug": slug.current, "category": category }`
)

const ARTICLE_QUERY = defineQuery(
  `*[_type == "article" && slug.current == $slug && ${LIVE}][0]{
    _id, title, metaTitle, slug, description, category,
    datePublished, dateModified, body, faqs,
    ogImage{ asset, alt }, focusKeyword, llmsContext,
    schemaOrgType, author, noindex
  }`
)

const ARTICLES_BY_CATEGORY_QUERY = defineQuery(
  `*[_type == "article" && category == $category && ${LIVE}] | order(datePublished desc){
    _id, title, slug, description, datePublished, dateModified, focusKeyword,
    "firstImage": body[@._type == "image"][0]{ asset, alt }
  }`
)

const ALL_ARTICLES_QUERY = defineQuery(
  `*[_type == "article" && ${LIVE}] | order(datePublished desc){
    _id, title, slug, description, category, datePublished
  }`
)

export async function getAllArticleSlugs() {
  return sanityClient.fetch(SLUGS_QUERY)
}

export async function getArticleBySlug(slug: string): Promise<SanityArticle | null> {
  return sanityClient.fetch(ARTICLE_QUERY, {slug})
}

export async function getArticlesByCategory(category: string): Promise<SanityArticle[]> {
  return sanityClient.fetch(ARTICLES_BY_CATEGORY_QUERY, {category})
}

export async function getAllArticles(): Promise<SanityArticle[]> {
  return sanityClient.fetch(ALL_ARTICLES_QUERY)
}
