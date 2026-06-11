<?php
/**
 * Plugin Name:       GeoReady — AI Visibility & AEO
 * Plugin URI:        https://geoready.dev
 * Description:       Make your WordPress site visible to AI answer engines (ChatGPT, Perplexity, Gemini). Generates llms.txt and AI discovery files, and scores your AI search readiness (GEO/AEO).
 * Version:           0.1.0
 * Requires at least: 5.8
 * Requires PHP:      7.4
 * Author:            Auriti Labs
 * Author URI:        https://geoready.dev
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       geoready
 *
 * @package GeoReady
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // No direct access.
}

define( 'GEOREADY_VERSION', '0.1.0' );
define( 'GEOREADY_PATH', plugin_dir_path( __FILE__ ) );
define( 'GEOREADY_URL', plugin_dir_url( __FILE__ ) );

require_once GEOREADY_PATH . 'includes/class-geoready-builder.php';
require_once GEOREADY_PATH . 'includes/class-geoready-files.php';
require_once GEOREADY_PATH . 'includes/class-geoready-admin.php';

/**
 * Default options, merged with stored ones.
 *
 * @return array
 */
function geoready_get_options() {
	$defaults = array(
		'enable_llms_txt'     => 1,
		'enable_ai_discovery' => 1,
		'site_name'           => '',
		'description'         => '',
		'post_types'          => array( 'page', 'post' ),
	);
	$stored = get_option( 'geoready_options', array() );
	return wp_parse_args( is_array( $stored ) ? $stored : array(), $defaults );
}

/**
 * Boot: register the virtual-file routes and the admin UI.
 */
function geoready_init() {
	( new GeoReady_Files( 'geoready_get_options' ) )->register();
	if ( is_admin() ) {
		( new GeoReady_Admin( 'geoready_get_options' ) )->register();
	}
}
add_action( 'init', 'geoready_init' );

/**
 * Flush rewrite rules on activation/deactivation so /llms.txt resolves.
 */
function geoready_activate() {
	( new GeoReady_Files( 'geoready_get_options' ) )->add_rewrite_rules();
	flush_rewrite_rules();
}
register_activation_hook( __FILE__, 'geoready_activate' );

/**
 * Clean up rewrite rules on deactivation.
 */
function geoready_deactivate() {
	flush_rewrite_rules();
}
register_deactivation_hook( __FILE__, 'geoready_deactivate' );
