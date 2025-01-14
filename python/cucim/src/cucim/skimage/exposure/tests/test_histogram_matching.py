import cupy as cp
import numpy as np
import pytest
from cupy.testing import assert_array_almost_equal
from numpy.testing import assert_almost_equal
from skimage import data

from cucim.skimage import exposure
from cucim.skimage.exposure import histogram_matching


@pytest.mark.parametrize('array, template, expected_array', [
    (cp.arange(10), cp.arange(100), cp.arange(9, 100, 10)),
    (cp.random.rand(4), cp.ones(3), cp.ones(4))
])
def test_match_array_values(array, template, expected_array):
    # when
    matched = histogram_matching._match_cumulative_cdf(array, template)

    # then
    assert_array_almost_equal(matched, expected_array)


class TestMatchHistogram:

    image_rgb = cp.asarray(data.chelsea())
    template_rgb = cp.asarray(data.astronaut())

    @pytest.mark.parametrize('image, reference, multichannel', [
        (image_rgb, template_rgb, True),
        (image_rgb[:, :, 0], template_rgb[:, :, 0], False)
    ])
    def test_match_histograms(self, image, reference, multichannel):
        """Assert that pdf of matched image is close to the reference's pdf for
        all channels and all values of matched"""

        # when
        matched = exposure.match_histograms(image, reference,
                                            multichannel=multichannel)

        matched = cp.asnumpy(matched)
        matched_pdf = self._calculate_image_empirical_pdf(matched)
        reference_pdf = self._calculate_image_empirical_pdf(
            cp.asnumpy(reference))

        # then
        for channel in range(len(matched_pdf)):
            reference_values, reference_quantiles = reference_pdf[channel]
            matched_values, matched_quantiles = matched_pdf[channel]

            for i, matched_value in enumerate(matched_values):
                closest_id = (
                    np.abs(reference_values - matched_value)
                ).argmin()
                assert_almost_equal(matched_quantiles[i],
                                    reference_quantiles[closest_id],
                                    decimal=1)

    @pytest.mark.parametrize('image, reference', [
        (image_rgb, template_rgb[:, :, 0]),
        (image_rgb[:, :, 0], template_rgb)
    ])
    def test_raises_value_error_on_channels_mismatch(self, image, reference):
        with pytest.raises(ValueError):
            exposure.match_histograms(image, reference)

    @classmethod
    def _calculate_image_empirical_pdf(cls, image):
        """Helper function for calculating empirical probability density
        function of a given image for all channels"""

        if image.ndim > 2:
            image = image.transpose(2, 0, 1)
        channels = np.array(image, copy=False, ndmin=3)

        channels_pdf = []
        for channel in channels:
            channel_values, counts = np.unique(channel, return_counts=True)
            channel_quantiles = np.cumsum(counts).astype(np.float64)
            channel_quantiles /= channel_quantiles[-1]

            channels_pdf.append((channel_values, channel_quantiles))

        return np.asarray(channels_pdf, dtype=object)
