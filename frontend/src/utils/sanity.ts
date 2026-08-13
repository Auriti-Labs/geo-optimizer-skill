import {sanityClient} from 'sanity:client'
import {defineQuery} from 'groq'
import imageUrlBuilder from '@sanity/image-url'

const imageBuilder = imageUrlBuilder(sanityClient)

export function urlForImage(source: {asset: {_ref: string}}) {
  return imageBuilder.image(source)
}

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
}

// An article is "live" if:
//   - status == "published"  (explicit publish)
//   - status == "scheduled" AND scheduledFor <= now()  (scheduled time passed)
//   - status is not yet set (legacy docs migrated before this field existed)
const LIVE = `(!defined(status) || status == "published" || (status == "scheduled" && dateTime(scheduledFor) <= dateTime(now())))`

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
    ogImage{ asset, alt }
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
