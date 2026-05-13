(function () {
    const csrfToken = getCsrfToken();
    const toast = document.querySelector("[data-toast]");
    const currencySymbol = "\u20b9";
    const isAuthenticated = document.body?.dataset.authenticated === "true";

    if (window.lucide) {
        window.lucide.createIcons();
    }

    document.querySelectorAll("img").forEach((image) => {
        if (image.complete && image.naturalWidth === 0) {
            markBrokenImage(image);
            return;
        }
        image.addEventListener("error", function () {
            markBrokenImage(this);
        }, { once: true });
    });

    setupLocationPicker();
    setupAuthModal();

    document.addEventListener("click", function (event) {
        const menuButton = event.target.closest("[data-mobile-menu]");
        if (menuButton) {
            document.querySelector("[data-nav-links]")?.classList.toggle("open");
        }

        const addButton = event.target.closest(".js-add-cart");
        if (addButton) {
            if (!isAuthenticated) {
                openAuthModal("Please login or sign up first to add food to your cart.");
                return;
            }
            addToCart(addButton.dataset.itemId, 1, false);
        }

        const qtyButton = event.target.closest(".js-qty");
        if (qtyButton) {
            const input = document.querySelector(`.qty-input[data-item-id="${qtyButton.dataset.itemId}"]`);
            const nextValue = Math.max(1, Number(input.value || 1) + Number(qtyButton.dataset.delta));
            input.value = nextValue;
            updateCart(qtyButton.dataset.itemId, nextValue);
        }

        const removeButton = event.target.closest(".js-remove-cart");
        if (removeButton) {
            removeCartItem(removeButton.dataset.itemId);
        }

        const clearButton = event.target.closest(".js-clear-cart");
        if (clearButton && confirm("Clear all items from your cart?")) {
            postJson("/cart/clear/", {}).then((data) => {
                updateCartUI(data.cart);
                showToast("Cart cleared.");
                window.location.reload();
            });
        }

        const locationPicker = event.target.closest("[data-location-picker]");
        if (!locationPicker) {
            closeLocationMenus();
        }

        if (event.target.closest("[data-auth-modal-close]")) {
            closeAuthModal();
        }

        if (event.target.closest("[data-open-premium-cancel]")) {
            openPremiumCancelModal();
        }

        if (event.target.closest("[data-premium-cancel-close]")) {
            closePremiumCancelModal();
        }
    });

    document.addEventListener("change", function (event) {
        if (event.target.matches(".qty-input")) {
            const quantity = Math.max(1, Number(event.target.value || 1));
            event.target.value = quantity;
            updateCart(event.target.dataset.itemId, quantity);
        }
    });

    document.querySelectorAll(".js-live-tracking").forEach(startLiveTracking);

    document.querySelector("[data-footer-track]")?.addEventListener("submit", function (event) {
        event.preventDefault();
        const code = new FormData(this).get("tracking_code")?.toString().trim();
        if (!code) {
            showToast("Enter a tracking code first.");
            return;
        }
        window.location.href = `/track/${encodeURIComponent(code.toUpperCase())}/`;
    });

    document.querySelector("[data-footer-newsletter]")?.addEventListener("submit", function (event) {
        event.preventDefault();
        const email = new FormData(this).get("email")?.toString().trim();
        if (!email || !email.includes("@")) {
            showToast("Enter a valid email address.");
            return;
        }
        window.localStorage.setItem("tonmoy_eats_footer_email", email);
        this.reset();
        showToast("Thanks. We will send Tonmoy Eats updates there.");
    });

    function addToCart(itemId, quantity, replace) {
        postJson("/cart/add/", { item_id: itemId, quantity: quantity, replace: replace })
            .then((data) => {
                updateCartUI(data.cart);
                showToast(data.message || "Added to cart.");
            })
            .catch((error) => {
                if (error.status === 409 && error.data?.requires_confirmation) {
                    if (confirm(error.data.message)) {
                        addToCart(itemId, quantity, true);
                    }
                    return;
                }
                if (error.status === 401 || error.data?.login_required) {
                    openAuthModal(error.data?.message || "Please login or sign up first.");
                    return;
                }
                showToast("Could not add item. Please try again.");
            });
    }

    function updateCart(itemId, quantity) {
        postJson("/cart/update/", { item_id: itemId, quantity: quantity }).then((data) => {
            updateCartUI(data.cart);
        });
    }

    function removeCartItem(itemId) {
        postJson("/cart/remove/", { item_id: itemId }).then((data) => {
            document.querySelector(`[data-cart-row="${itemId}"]`)?.remove();
            updateCartUI(data.cart);
            showToast("Item removed.");
            if (data.cart.count === 0) {
                window.location.reload();
            }
        });
    }

    function updateCartUI(cart) {
        if (!cart) {
            return;
        }
        document.querySelectorAll("[data-cart-count]").forEach((node) => {
            node.textContent = cart.count;
        });
        setText("[data-summary-restaurant]", cart.restaurant || "Not selected");
        setText("[data-summary-subtotal]", cart.subtotal);
        setText("[data-summary-delivery]", cart.delivery_fee);
        setText("[data-summary-discount]", cart.discount);
        setText("[data-summary-tax]", cart.tax);
        setText("[data-summary-total]", cart.total);
        cart.items.forEach((item) => {
            setText(`[data-line-total="${item.id}"]`, `${currencySymbol}${item.line_total}`);
        });
    }

    function setText(selector, value) {
        document.querySelectorAll(selector).forEach((node) => {
            node.textContent = value;
        });
    }

    function setupLocationPicker() {
        document.querySelectorAll("[data-location-picker]").forEach((picker) => {
            const toggle = picker.querySelector("[data-location-toggle]");
            const label = picker.querySelector("[data-location-label]");
            const input = picker.querySelector("[data-location-input]");
            const savedLocation = window.localStorage.getItem("tonmoy_eats_location");

            if (savedLocation) {
                setLocationValue(picker, savedLocation);
            } else {
                setLocationValue(picker, input?.value || "Tezpur");
            }

            toggle?.addEventListener("click", function () {
                const isOpen = picker.classList.toggle("open");
                toggle.setAttribute("aria-expanded", String(isOpen));
            });

            picker.querySelectorAll("[data-location-option]").forEach((option) => {
                option.addEventListener("click", function () {
                    setLocationValue(picker, option.dataset.locationOption);
                    closeLocationMenus();
                    showToast(`Delivering around ${option.dataset.locationOption}.`);
                });
            });

            picker.querySelectorAll("[data-location-soon]").forEach((option) => {
                option.addEventListener("click", function () {
                    closeLocationMenus();
                    showToast(`${option.dataset.locationSoon} is coming soon.`);
                });
            });

            picker.querySelector("[data-location-detect]")?.addEventListener("click", function () {
                if (!navigator.geolocation) {
                    showToast("Location detection is not supported in this browser.");
                    return;
                }
                showToast("Checking your current location...");
                navigator.geolocation.getCurrentPosition(
                    () => {
                        setLocationValue(picker, "Current location");
                        closeLocationMenus();
                        showToast("Current location selected.");
                    },
                    () => {
                        setLocationValue(picker, "Tezpur");
                        closeLocationMenus();
                        showToast("Location permission denied. Tezpur selected.");
                    },
                    { enableHighAccuracy: true, timeout: 8000, maximumAge: 600000 }
                );
            });

            function setLocationValue(currentPicker, value) {
                if (!value) {
                    return;
                }
                label.textContent = value;
                input.value = value;
                window.localStorage.setItem("tonmoy_eats_location", value);
            }
        });
    }

    function closeLocationMenus() {
        document.querySelectorAll("[data-location-picker].open").forEach((picker) => {
            picker.classList.remove("open");
            picker.querySelector("[data-location-toggle]")?.setAttribute("aria-expanded", "false");
        });
    }

    function setupAuthModal() {
        const modal = document.querySelector("[data-auth-modal]");
        if (!modal || isAuthenticated) {
            return;
        }
        if (!window.sessionStorage.getItem("tonmoy_eats_auth_prompt_seen")) {
            window.setTimeout(() => {
                openAuthModal();
                window.sessionStorage.setItem("tonmoy_eats_auth_prompt_seen", "1");
            }, 350);
        }
    }

    function openAuthModal(message) {
        const modal = document.querySelector("[data-auth-modal]");
        if (!modal) {
            showToast(message || "Please login or sign up first.");
            return;
        }
        if (message) {
            const text = modal.querySelector("p");
            if (text) {
                text.textContent = message;
            }
        }
        modal.classList.add("open");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
    }

    function closeAuthModal() {
        const modal = document.querySelector("[data-auth-modal]");
        if (!modal) {
            return;
        }
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("modal-open");
    }

    function openPremiumCancelModal() {
        const modal = document.querySelector("[data-premium-cancel-modal]");
        if (!modal) {
            return;
        }
        modal.classList.add("open");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
    }

    function closePremiumCancelModal() {
        const modal = document.querySelector("[data-premium-cancel-modal]");
        if (!modal) {
            return;
        }
        modal.classList.remove("open");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("modal-open");
    }

    function startLiveTracking(node) {
        const url = node.dataset.statusUrl;
        if (!url) {
            return;
        }
        const refresh = () => {
            fetch(url, { headers: { "Accept": "application/json" } })
                .then((response) => response.json())
                .then((data) => {
                    setText("[data-live-status]", data.status_label);
                    const progress = node.querySelector("[data-live-progress]");
                    const marker = node.querySelector("[data-live-marker]");
                    if (progress) {
                        progress.style.width = `${data.progress}%`;
                    }
                    if (marker) {
                        marker.style.left = `${data.progress}%`;
                    }
                    node.querySelectorAll("[data-step]").forEach((step) => {
                        const current = data.steps.find((entry) => entry.key === step.dataset.step);
                        step.classList.toggle("complete", Boolean(current?.complete));
                    });
                })
                .catch(() => {});
        };
        refresh();
        window.setInterval(refresh, 8000);
    }

    function postJson(url, payload) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
                "Accept": "application/json",
            },
            body: JSON.stringify(payload),
        }).then(async (response) => {
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw { status: response.status, data: data };
            }
            return data;
        });
    }

    function getCsrfToken() {
        const meta = document.querySelector("meta[name='csrf-token']");
        if (meta?.content && meta.content !== "NOTPROVIDED") {
            return meta.content;
        }
        const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function showToast(message) {
        if (!toast) {
            return;
        }
        toast.textContent = message;
        toast.classList.add("show");
        window.clearTimeout(showToast.timer);
        showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
    }

    function markBrokenImage(image) {
        image.parentElement?.classList.add("image-fallback");
        image.remove();
    }
})();
