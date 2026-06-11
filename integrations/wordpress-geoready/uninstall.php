<?php
/**
 * GeoReady uninstall — remove plugin options.
 *
 * @package GeoReady
 */

if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
	exit;
}

delete_option( 'geoready_options' );
