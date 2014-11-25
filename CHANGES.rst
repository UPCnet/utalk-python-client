CHANGELOG
=========

1.0 (unreleased)
-------------------

 * Handle stomp errors as exceptions Better logging store received times on client [Carles Bruguera]
 * handle close frames [Carles Bruguera]
 * Add extra wait between connects [Carles Bruguera]
 * Log message reception times [Carles Bruguera]
 * Enable logintoken cli param [Carles Bruguera]
 * Don't block when waiting to send a message Save time stats with sent date Don't start immediately, wait start_delay [Carles Bruguera]
 * Catch acces denied errors and retry [Carles Bruguera]
 * Collect stats [Carles Bruguera]
 * Enable login with token. Connect on start [Carles Bruguera]
 * User urlparse to extract domain [Carles Bruguera]
 * Include client info in stomp headers [Carles Bruguera]
 * Missing dependencies [Carles Bruguera]
 * Add xhr_streaming transport Add param to override utalk server [Carles Bruguera]
 * Make transports gevent aware [Carles Bruguera]
 * Move all sockjs implementation bits to transports Document classes and methods [Carles Bruguera]
 * A Fucking Working Websocket client (#ohyeah) [Carles Bruguera]
 * Finally fix utalk client Use xhr polling by default Refactor SockJS part into transports class [Carles Bruguera]
 * Change to ws4py [Carles Bruguera]
 * Improve base client Finish test client [Carles Bruguera]
 * Trigger events Log using wrapper method Log new conversations [Carles Bruguera]
 * Add test client skeleton [Carles Bruguera]
 * Move sockjs syntax bits out of stomp Send message method [Carles Bruguera]
 * Import existing code [Carles Bruguera]
