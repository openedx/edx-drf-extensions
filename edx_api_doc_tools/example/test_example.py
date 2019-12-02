"""
Make sure our example API works,
so that we're not testing our doc tools on a broken API.
"""
import json

from django.test import SimpleTestCase
from django.test.utils import override_settings

from . import urls as example_urls


@override_settings(ROOT_URLCONF=example_urls.__name__)
class HedgehogViewTest(SimpleTestCase):
    """
    Test the HedgehogViewSet.
    """
    new_hog = {
        'uuid': '44444444-4444-4444-4444-444444444444',
        'key': 'erin',
        'name': "Erin Aceinae",
        'weight_grams': 432,
        'fav_food': "strawberries",
        'is_college_graduate': True,
    }
    updated_hog = {
        'name': "Cornelius Quillson",
        'weight_grams': 465,
    }
    invalid_hog = {
        'key': 'nope',
        'name': 'Nopey McNopeface',
        # (missing the other required fields)
    }

    def request(self, method, path, data=None):
        """
        Make a `method` request to `path` in the hedgehog API with (optional) `data`.
        """
        request_method = getattr(self.client, method.lower())
        args = ['/api/hedgehog/v0/{}'.format(path)]
        if data:
            args.append(json.dumps(data))
        return request_method(*args, content_type='application/json')

    def test_list(self):
        response = self.request('get', 'hogs/')
        assert response.status_code == 200
        assert len(response.data) == 5

    def test_get(self):
        response = self.request('get', 'hogs/pepper/')
        assert response.status_code == 200
        assert response.data['name'] == 'Pepper Pokes'

    def test_post(self):
        response = self.request('post', 'hogs/', self.new_hog)
        assert response.status_code == 501

    def test_post_400(self):
        response = self.request('post', 'hogs/', self.invalid_hog)
        assert response.status_code == 400

    def test_put(self):
        response = self.request('put', 'hogs/skip/', self.new_hog)
        assert response.status_code == 501

    def test_put_404(self):
        response = self.request('put', 'hogs/erin/', self.new_hog)
        assert response.status_code == 404

    def test_patch(self):
        response = self.request('patch', 'hogs/skip/', self.updated_hog)
        assert response.status_code == 501

    def test_patch_404(self):
        response = self.request('patch', 'hogs/erin/', self.new_hog)
        assert response.status_code == 404

    def test_destroy(self):
        response = self.request('delete', 'hogs/skip/')
        assert response.status_code == 501

    def test_destroy_404(self):
        response = self.request('delete', 'hogs/erin/')
        assert response.status_code == 404
