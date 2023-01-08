'use strict';

$(function () {
    $("#add-comment-button").click(function (e) {
        $("#add-comment-panel").toggleClass("active");
    });
    $("#add-comment-panel .close").click(function (e) {
        $("#add-comment-panel").removeClass("active");
    });
});