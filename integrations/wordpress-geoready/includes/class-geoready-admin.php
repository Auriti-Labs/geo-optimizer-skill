<?php
/**
 * GeoReady — admin settings page + live AI visibility check.
 *
 * Adds Settings → GeoReady: toggles for the generated files, site name /
 * description overrides, post-type selection, and a "Check my AI visibility"
 * button that scores the site via the public GeoReady audit API and shows the
 * GEO score, band, and top recommendations — with a CTA to track it over time.
 *
 * @package GeoReady
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Settings screen and AJAX audit handler.
 */
class GeoReady_Admin {

	const AUDIT_ENDPOINT = 'https://geoready.dev/api/audit';
	const NONCE_ACTION   = 'geoready_audit';

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
	 * Hook into WordPress admin.
	 */
	public function register() {
		add_action( 'admin_menu', array( $this, 'add_menu' ) );
		add_action( 'admin_init', array( $this, 'register_settings' ) );
		add_action( 'wp_ajax_geoready_audit', array( $this, 'ajax_audit' ) );
	}

	/**
	 * Settings → GeoReady.
	 */
	public function add_menu() {
		add_options_page(
			__( 'GeoReady — AI Visibility', 'geoready' ),
			__( 'GeoReady', 'geoready' ),
			'manage_options',
			'geoready',
			array( $this, 'render_page' )
		);
	}

	/**
	 * Register the single options array with a sanitizer.
	 */
	public function register_settings() {
		register_setting(
			'geoready',
			'geoready_options',
			array( 'sanitize_callback' => array( $this, 'sanitize' ) )
		);
	}

	/**
	 * Sanitize submitted options.
	 *
	 * @param array $input Raw input.
	 * @return array
	 */
	public function sanitize( $input ) {
		$input = is_array( $input ) ? $input : array();
		$valid_types = get_post_types( array( 'public' => true ), 'names' );
		$types = array();
		if ( ! empty( $input['post_types'] ) && is_array( $input['post_types'] ) ) {
			foreach ( $input['post_types'] as $type ) {
				if ( in_array( $type, $valid_types, true ) ) {
					$types[] = sanitize_key( $type );
				}
			}
		}
		return array(
			'enable_llms_txt'     => empty( $input['enable_llms_txt'] ) ? 0 : 1,
			'enable_ai_discovery' => empty( $input['enable_ai_discovery'] ) ? 0 : 1,
			'site_name'           => isset( $input['site_name'] ) ? sanitize_text_field( $input['site_name'] ) : '',
			'description'         => isset( $input['description'] ) ? sanitize_text_field( $input['description'] ) : '',
			'post_types'          => ! empty( $types ) ? $types : array( 'page', 'post' ),
		);
	}

	/**
	 * Render the settings page.
	 */
	public function render_page() {
		if ( ! current_user_can( 'manage_options' ) ) {
			return;
		}
		$options    = call_user_func( $this->options_provider );
		$public_pt  = get_post_types( array( 'public' => true ), 'objects' );
		$ajax_nonce = wp_create_nonce( self::NONCE_ACTION );
		?>
		<div class="wrap">
			<h1><?php esc_html_e( 'GeoReady — AI Visibility & AEO', 'geoready' ); ?></h1>
			<p>
				<?php esc_html_e( 'Make this site visible to AI answer engines (ChatGPT, Perplexity, Gemini). GeoReady generates the AI discovery files and scores your AI search readiness.', 'geoready' ); ?>
			</p>

			<h2><?php esc_html_e( 'Check your AI visibility', 'geoready' ); ?></h2>
			<p>
				<button class="button button-primary" id="geoready-audit-btn"><?php esc_html_e( 'Check my AI visibility now', 'geoready' ); ?></button>
				<span id="geoready-audit-status" style="margin-left:8px;"></span>
			</p>
			<div id="geoready-audit-result" style="margin:12px 0;max-width:680px;"></div>

			<form method="post" action="options.php">
				<?php settings_fields( 'geoready' ); ?>
				<h2><?php esc_html_e( 'Generated files', 'geoready' ); ?></h2>
				<table class="form-table" role="presentation">
					<tr>
						<th scope="row"><?php esc_html_e( 'llms.txt', 'geoready' ); ?></th>
						<td>
							<label>
								<input type="checkbox" name="geoready_options[enable_llms_txt]" value="1" <?php checked( ! empty( $options['enable_llms_txt'] ) ); ?> />
								<?php
								printf(
									/* translators: %s: llms.txt URL */
									esc_html__( 'Serve %s from published content', 'geoready' ),
									'<code>' . esc_html( home_url( '/llms.txt' ) ) . '</code>'
								);
								?>
							</label>
						</td>
					</tr>
					<tr>
						<th scope="row"><?php esc_html_e( 'AI discovery files', 'geoready' ); ?></th>
						<td>
							<label>
								<input type="checkbox" name="geoready_options[enable_ai_discovery]" value="1" <?php checked( ! empty( $options['enable_ai_discovery'] ) ); ?> />
								<?php
								printf(
									/* translators: 1: ai.txt URL, 2: summary.json URL */
									esc_html__( 'Serve %1$s and %2$s', 'geoready' ),
									'<code>/.well-known/ai.txt</code>',
									'<code>/ai/summary.json</code>'
								);
								?>
							</label>
						</td>
					</tr>
				</table>

				<h2><?php esc_html_e( 'Content', 'geoready' ); ?></h2>
				<table class="form-table" role="presentation">
					<tr>
						<th scope="row"><label for="geoready_site_name"><?php esc_html_e( 'Site name', 'geoready' ); ?></label></th>
						<td>
							<input type="text" id="geoready_site_name" class="regular-text" name="geoready_options[site_name]" value="<?php echo esc_attr( $options['site_name'] ); ?>" placeholder="<?php echo esc_attr( get_bloginfo( 'name' ) ); ?>" />
							<p class="description"><?php esc_html_e( 'Leave blank to use the site title.', 'geoready' ); ?></p>
						</td>
					</tr>
					<tr>
						<th scope="row"><label for="geoready_description"><?php esc_html_e( 'Description', 'geoready' ); ?></label></th>
						<td>
							<input type="text" id="geoready_description" class="large-text" name="geoready_options[description]" value="<?php echo esc_attr( $options['description'] ); ?>" placeholder="<?php echo esc_attr( get_bloginfo( 'description' ) ); ?>" />
						</td>
					</tr>
					<tr>
						<th scope="row"><?php esc_html_e( 'Include post types', 'geoready' ); ?></th>
						<td>
							<?php foreach ( $public_pt as $pt ) : ?>
								<?php if ( 'attachment' === $pt->name ) { continue; } ?>
								<label style="display:inline-block;margin-right:12px;">
									<input type="checkbox" name="geoready_options[post_types][]" value="<?php echo esc_attr( $pt->name ); ?>" <?php checked( in_array( $pt->name, (array) $options['post_types'], true ) ); ?> />
									<?php echo esc_html( $pt->labels->name ); ?>
								</label>
							<?php endforeach; ?>
						</td>
					</tr>
				</table>
				<?php submit_button(); ?>
			</form>

			<p style="margin-top:16px;color:#555;">
				<?php
				printf(
					/* translators: %s: GeoReady link */
					esc_html__( 'Want continuous monitoring, score history, and AI citation tracking? %s', 'geoready' ),
					'<a href="https://geoready.dev?utm_source=wp-plugin" target="_blank" rel="noopener">geoready.dev</a>'
				);
				?>
			</p>
		</div>

		<script>
		( function () {
			var btn = document.getElementById( 'geoready-audit-btn' );
			if ( ! btn ) { return; }
			btn.addEventListener( 'click', function ( e ) {
				e.preventDefault();
				var status = document.getElementById( 'geoready-audit-status' );
				var result = document.getElementById( 'geoready-audit-result' );
				btn.disabled = true;
				status.textContent = <?php echo wp_json_encode( __( 'Auditing… (~10s)', 'geoready' ) ); ?>;
				result.innerHTML = '';
				var body = new URLSearchParams();
				body.append( 'action', 'geoready_audit' );
				body.append( 'nonce', <?php echo wp_json_encode( $ajax_nonce ); ?> );
				fetch( <?php echo wp_json_encode( admin_url( 'admin-ajax.php' ) ); ?>, {
					method: 'POST',
					headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
					body: body.toString()
				} ).then( function ( r ) { return r.json(); } ).then( function ( data ) {
					btn.disabled = false;
					status.textContent = '';
					if ( ! data || ! data.success ) {
						result.innerHTML = '<div class="notice notice-error inline"><p>' + ( data && data.data ? data.data : 'Audit failed.' ) + '</p></div>';
						return;
					}
					result.innerHTML = data.data.html;
				} ).catch( function () {
					btn.disabled = false;
					status.textContent = '';
					result.innerHTML = '<div class="notice notice-error inline"><p>Network error.</p></div>';
				} );
			} );
		} )();
		</script>
		<?php
	}

	/**
	 * AJAX: audit the current site via the public API and return rendered HTML.
	 */
	public function ajax_audit() {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_send_json_error( __( 'Permission denied.', 'geoready' ), 403 );
		}
		check_ajax_referer( self::NONCE_ACTION, 'nonce' );

		$url      = home_url();
		$response = wp_remote_get(
			add_query_arg( 'url', rawurlencode( $url ), self::AUDIT_ENDPOINT ),
			array(
				'timeout' => 30,
				'headers' => array( 'Accept' => 'application/json' ),
			)
		);

		if ( is_wp_error( $response ) ) {
			wp_send_json_error( __( 'Could not reach the audit service. Try again.', 'geoready' ) );
		}
		$code = wp_remote_retrieve_response_code( $response );
		if ( 200 !== (int) $code ) {
			wp_send_json_error( __( 'The audit service returned an error. Try again.', 'geoready' ) );
		}
		$data = json_decode( wp_remote_retrieve_body( $response ), true );
		if ( ! is_array( $data ) || ! isset( $data['score'] ) ) {
			wp_send_json_error( __( 'Unexpected response from the audit service.', 'geoready' ) );
		}

		wp_send_json_success( array( 'html' => $this->render_audit_result( $data ) ) );
	}

	/**
	 * Render the audit result as safe HTML.
	 *
	 * @param array $data Audit JSON.
	 * @return string
	 */
	private function render_audit_result( array $data ) {
		$score = (int) $data['score'];
		$band  = isset( $data['band'] ) ? (string) $data['band'] : '';
		$colors = array(
			'excellent'  => '#16a34a',
			'good'       => '#0891b2',
			'foundation' => '#ca8a04',
			'critical'   => '#dc2626',
		);
		$color = isset( $colors[ $band ] ) ? $colors[ $band ] : '#555';

		$recs = array();
		if ( ! empty( $data['recommendations'] ) && is_array( $data['recommendations'] ) ) {
			$recs = array_slice( $data['recommendations'], 0, 5 );
		}

		ob_start();
		?>
		<div style="border:1px solid #ccd0d4;border-radius:8px;padding:16px;background:#fff;">
			<div style="display:flex;align-items:baseline;gap:12px;">
				<span style="font-size:34px;font-weight:700;color:<?php echo esc_attr( $color ); ?>;"><?php echo esc_html( $score ); ?></span>
				<span style="color:#555;">/ 100</span>
				<strong style="text-transform:uppercase;color:<?php echo esc_attr( $color ); ?>;"><?php echo esc_html( $band ); ?></strong>
				<span style="color:#777;">— AI search readiness</span>
			</div>
			<?php if ( ! empty( $recs ) ) : ?>
				<p style="margin:12px 0 4px;font-weight:600;"><?php esc_html_e( 'Top fixes:', 'geoready' ); ?></p>
				<ul style="margin:0 0 0 18px;list-style:disc;">
					<?php foreach ( $recs as $rec ) : ?>
						<li style="margin-bottom:4px;"><?php echo esc_html( $rec ); ?></li>
					<?php endforeach; ?>
				</ul>
			<?php endif; ?>
			<p style="margin-top:14px;">
				<a class="button" href="https://app.geoready.dev/signup?utm_source=wp-plugin&amp;intent=citations" target="_blank" rel="noopener"><?php esc_html_e( 'Track this score over time →', 'geoready' ); ?></a>
			</p>
		</div>
		<?php
		return ob_get_clean();
	}
}
