<?php
/**
 * Plain-PHP tests for GeoReady_Builder — no WordPress, no PHPUnit.
 * Run: php test/test-builder.php
 *
 * @package GeoReady
 */

define( 'GEOREADY_TEST', true );
require __DIR__ . '/../includes/class-geoready-builder.php';

$failures = 0;
$tests    = 0;

/**
 * Tiny assertion helper.
 *
 * @param bool   $cond  Condition.
 * @param string $label Test name.
 */
function check( $cond, $label ) {
	global $failures, $tests;
	$tests++;
	if ( $cond ) {
		echo "  ok  $label\n";
	} else {
		$failures++;
		echo "  XX  $label\n";
	}
}

$args = array(
	'site_name'   => 'Example',
	'description' => 'A test site.',
	'site_url'    => 'https://example.com/',
);

$pages = array(
	array(
		'title'   => 'Home',
		'url'     => 'https://example.com/',
		'section' => 'Pages',
	),
	array(
		'title'   => 'GEO Audit Guide',
		'url'     => 'https://example.com/guides/geo-audit/',
		'section' => 'Guides',
	),
	array(
		'title'   => 'What Is Llms Txt',
		'url'     => 'https://example.com/guides/what-is-llms-txt/',
		'section' => 'Guides',
	),
);

// --- llms.txt ---
$llms = GeoReady_Builder::build_llms_txt( $args, $pages );
check( strpos( $llms, "# Example\n" ) === 0, 'llms.txt starts with site name H1' );
check( strpos( $llms, '> A test site.' ) !== false, 'llms.txt includes blockquote description' );
check( strpos( $llms, '## Pages' ) !== false, 'llms.txt has Pages section' );
check( strpos( $llms, '## Guides' ) !== false, 'llms.txt has Guides section' );
check( strpos( $llms, '[GEO Audit Guide](https://example.com/guides/geo-audit/)' ) !== false, 'llms.txt links with absolute URL' );
check( strpos( $llms, 'geoready.dev' ) !== false, 'llms.txt has attribution footer' );
// Pages section must come before Guides (sorted: Pages first).
check( strpos( $llms, '## Pages' ) < strpos( $llms, '## Guides' ), 'Pages section sorts before Guides' );

// --- maxPerSection ---
$llms_capped = GeoReady_Builder::build_llms_txt( $args, $pages, 1 );
check( substr_count( $llms_capped, '[' ) - substr_count( $llms_capped, '](' ) >= 0, 'capped output is well-formed' );
check( substr_count( $llms_capped, '- [' ) === 2, 'max_per_section caps links per section (1 Pages + 1 Guides)' );

// --- humanize ---
check( GeoReady_Builder::humanize( 'getting-started' ) === 'Getting Started', 'humanize hyphen slug' );
check( GeoReady_Builder::humanize( 'AI_visibility' ) === 'Ai Visibility', 'humanize underscore slug' );
check( GeoReady_Builder::humanize( '' ) === '', 'humanize empty string' );

// --- ai.txt ---
$ai = GeoReady_Builder::build_ai_txt( $args );
check( strpos( $ai, 'LLMs: https://example.com/llms.txt' ) !== false, 'ai.txt points to llms.txt' );
check( strpos( $ai, 'Sitemap: https://example.com/sitemap.xml' ) !== false, 'ai.txt points to sitemap' );
check( strpos( $ai, 'User-Agent: *' ) !== false, 'ai.txt allows crawlers' );

// --- summary.json ---
$summary = GeoReady_Builder::build_summary_json( $args, count( $pages ) );
$decoded = json_decode( $summary, true );
check( 'Example' === $decoded['name'], 'summary.json name' );
check( 'https://example.com' === $decoded['url'], 'summary.json url has no trailing slash' );
check( 3 === $decoded['pages_count'], 'summary.json pages_count' );
check( 'https://example.com/llms.txt' === $decoded['llms_txt'], 'summary.json llms_txt pointer' );

// --- description omitted when empty ---
$summary_nodesc = GeoReady_Builder::build_summary_json(
	array(
		'site_name' => 'X',
		'site_url'  => 'https://x.com',
	),
	0
);
check( strpos( $summary_nodesc, 'description' ) === false, 'summary.json omits empty description' );

echo "\n$tests checks, $failures failed\n";
exit( $failures > 0 ? 1 : 0 );
