<?php
/**
 * GeoReady — serve the AI discovery files as virtual routes.
 *
 * Registers /llms.txt, /.well-known/ai.txt, and /ai/summary.json as rewrite
 * rules and renders them on the fly from published content. A real static
 * file at the same path (e.g. a hand-curated public/llms.txt) is never
 * shadowed: the rewrite only fires when the request reaches WordPress, which
 * it does only if no file exists there.
 *
 * @package GeoReady
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Registers and renders the virtual AI-discovery routes.
 */
class GeoReady_Files {

	/**
	 * Callable returning the plugin options array.
	 *
	 * @var callable
	 */
	private $options_provider;

	/**
	 * @param callable $options_provider Returns the options array.
	 */
	public function __construct( $options_provider ) {
		$this->options_provider = $options_provider;
	}

	/**
	 * Hook into WordPress. Called on `init`, so the rewrite rules are
	 * registered directly (re-hooking `init` from within `init` is fragile);
	 * query_vars and template_redirect fire later and are added normally.
	 */
	public function register() {
		$this->add_rewrite_rules();
		add_filter( 'query_vars', array( $this, 'add_query_var' ) );
		add_action( 'template_redirect', array( $this, 'maybe_render' ) );
	}

	/**
	 * Register the three virtual routes.
	 */
	public function add_rewrite_rules() {
		add_rewrite_rule( '^llms\.txt$', 'index.php?geoready_file=llms', 'top' );
		add_rewrite_rule( '^\.well-known/ai\.txt$', 'index.php?geoready_file=ai', 'top' );
		add_rewrite_rule( '^ai/summary\.json$', 'index.php?geoready_file=summary', 'top' );
	}

	/**
	 * Whitelist our query var.
	 *
	 * @param array $vars Query vars.
	 * @return array
	 */
	public function add_query_var( $vars ) {
		$vars[] = 'geoready_file';
		return $vars;
	}

	/**
	 * Render the requested file, or bail to normal handling.
	 */
	public function maybe_render() {
		$which = get_query_var( 'geoready_file' );
		if ( empty( $which ) ) {
			return;
		}
		$response = $this->build_response( $which, call_user_func( $this->options_provider ) );
		if ( null === $response ) {
			return;
		}
		$this->send( $response['content_type'], $response['body'] );
	}

	/**
	 * Build the response for a route. Pure of side effects (no headers/exit),
	 * so it is unit-testable with stubbed WordPress functions.
	 *
	 * @param string $which   One of llms|ai|summary.
	 * @param array  $options Plugin options.
	 * @return array|null { content_type, body } or null to bail.
	 */
	public function build_response( $which, array $options ) {
		$args = $this->build_args( $options );

		if ( 'llms' === $which ) {
			if ( empty( $options['enable_llms_txt'] ) ) {
				return null;
			}
			$pages = $this->collect_pages( $options );
			return array(
				'content_type' => 'text/plain',
				'body'         => GeoReady_Builder::build_llms_txt( $args, $pages ),
			);
		}
		if ( 'ai' === $which ) {
			if ( empty( $options['enable_ai_discovery'] ) ) {
				return null;
			}
			return array(
				'content_type' => 'text/plain',
				'body'         => GeoReady_Builder::build_ai_txt( $args ),
			);
		}
		if ( 'summary' === $which ) {
			if ( empty( $options['enable_ai_discovery'] ) ) {
				return null;
			}
			$count = count( $this->collect_pages( $options ) );
			return array(
				'content_type' => 'application/json',
				'body'         => GeoReady_Builder::build_summary_json( $args, $count ),
			);
		}
		return null;
	}

	/**
	 * Resolve site name / description / URL from options + WP defaults.
	 *
	 * @param array $options Plugin options.
	 * @return array
	 */
	private function build_args( array $options ) {
		$name = '' !== $options['site_name'] ? $options['site_name'] : get_bloginfo( 'name' );
		$desc = '' !== $options['description'] ? $options['description'] : get_bloginfo( 'description' );
		return array(
			'site_name'   => $name,
			'description' => $desc,
			'site_url'    => home_url(),
		);
	}

	/**
	 * Collect published content as page entries grouped by post type.
	 *
	 * @param array $options Plugin options.
	 * @return array
	 */
	private function collect_pages( array $options ) {
		$post_types = ! empty( $options['post_types'] ) ? (array) $options['post_types'] : array( 'page', 'post' );

		$query = new WP_Query(
			array(
				'post_type'              => $post_types,
				'post_status'            => 'publish',
				'posts_per_page'         => 200,
				'orderby'                => 'menu_order title',
				'order'                  => 'ASC',
				'no_found_rows'          => true,
				'update_post_meta_cache' => false,
				'update_post_term_cache' => false,
			)
		);

		$pages = array();
		foreach ( $query->posts as $post ) {
			$type_obj = get_post_type_object( $post->post_type );
			$section  = $type_obj && isset( $type_obj->labels->name ) ? $type_obj->labels->name : 'Pages';
			$pages[]  = array(
				'title'   => get_the_title( $post ),
				'url'     => get_permalink( $post ),
				'section' => 'page' === $post->post_type ? 'Pages' : $section,
			);
		}
		wp_reset_postdata();
		return $pages;
	}

	/**
	 * Emit a response and stop.
	 *
	 * @param string $content_type MIME type.
	 * @param string $body         Response body.
	 */
	private function send( $content_type, $body ) {
		if ( ! headers_sent() ) {
			header( 'Content-Type: ' . $content_type . '; charset=utf-8' );
			header( 'X-Robots-Tag: noindex' );
		}
		echo $body; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- plain-text artifact, not HTML.
		exit;
	}
}
