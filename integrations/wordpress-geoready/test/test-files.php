<?php
/**
 * Integration test for GeoReady_Files with stubbed WordPress functions.
 * Run: php test/test-files.php
 *
 * Exercises build_response() (the WP-coupled wiring) without a real WordPress:
 * the WP functions it depends on are stubbed below.
 *
 * @package GeoReady
 */

define( 'GEOREADY_TEST', true );
define( 'ABSPATH', __DIR__ );

// --- Minimal WordPress stubs ---
function home_url( $path = '' ) {
	return 'https://example.com' . $path;
}
function get_bloginfo( $key ) {
	return 'name' === $key ? 'Example Blog' : 'Tagline here';
}
function get_post_type_object( $type ) {
	$labels = (object) array( 'name' => ucfirst( $type ) . 's' );
	return (object) array( 'labels' => $labels );
}
function get_the_title( $post ) {
	return $post->title;
}
function get_permalink( $post ) {
	return 'https://example.com/' . $post->slug . '/';
}
function wp_reset_postdata() {}

class WP_Query {
	public $posts;
	public function __construct( $args ) {
		// Two pages + one post, regardless of args (stub).
		$this->posts = array(
			(object) array(
				'post_type' => 'page',
				'title'     => 'Home',
				'slug'      => '',
			),
			(object) array(
				'post_type' => 'page',
				'title'     => 'About',
				'slug'      => 'about',
			),
			(object) array(
				'post_type' => 'post',
				'title'     => 'GEO Audit Guide',
				'slug'      => 'geo-audit-guide',
			),
		);
	}
}

require __DIR__ . '/../includes/class-geoready-builder.php';
require __DIR__ . '/../includes/class-geoready-files.php';

$failures = 0;
$tests    = 0;
function check( $cond, $label ) {
	global $failures, $tests;
	$tests++;
	echo ( $cond ? '  ok  ' : '  XX  ' ) . $label . "\n";
	if ( ! $cond ) {
		$failures++;
	}
}

$options = array(
	'enable_llms_txt'     => 1,
	'enable_ai_discovery' => 1,
	'site_name'           => '',
	'description'         => '',
	'post_types'          => array( 'page', 'post' ),
);

$files = new GeoReady_Files(
	static function () use ( $options ) {
		return $options;
	}
);

// llms.txt from stubbed content.
$llms = $files->build_response( 'llms', $options );
check( 'text/plain' === $llms['content_type'], 'llms content-type is text/plain' );
check( strpos( $llms['body'], '# Example Blog' ) === 0, 'llms uses site title when name blank' );
check( strpos( $llms['body'], '## Pages' ) !== false, 'pages grouped under Pages' );
check( strpos( $llms['body'], '## Posts' ) !== false, 'posts grouped under post-type label' );
check( strpos( $llms['body'], '[GEO Audit Guide](https://example.com/geo-audit-guide/)' ) !== false, 'post links with permalink' );

// summary.json reflects the 3 stubbed entries.
$summary = $files->build_response( 'summary', $options );
$decoded = json_decode( $summary['body'], true );
check( 'application/json' === $summary['content_type'], 'summary content-type is json' );
check( 3 === $decoded['pages_count'], 'summary counts all entries' );
check( 'Example Blog' === $decoded['name'], 'summary uses site title' );

// ai.txt.
$ai = $files->build_response( 'ai', $options );
check( strpos( $ai['body'], 'LLMs: https://example.com/llms.txt' ) !== false, 'ai.txt points to llms.txt' );

// Toggles bail out.
$off = array_merge( $options, array( 'enable_llms_txt' => 0 ) );
check( null === $files->build_response( 'llms', $off ), 'llms disabled returns null' );
$off2 = array_merge( $options, array( 'enable_ai_discovery' => 0 ) );
check( null === $files->build_response( 'ai', $off2 ), 'ai discovery disabled returns null' );
check( null === $files->build_response( 'bogus', $options ), 'unknown route returns null' );

echo "\n$tests checks, $failures failed\n";
exit( $failures > 0 ? 1 : 0 );
