import re
from decimal import Decimal
from rest_framework import serializers
from .models import Calificacion


class CalificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calificacion
        fields = ['id', 'rut', 'anio', 'monto', 'factor', 'estado',
                  'fecha_registro', 'actualizado_en', 'creado_por', 'activo']
        read_only_fields = ['id', 'estado', 'fecha_registro', 'actualizado_en', 'creado_por', 'activo']

    def validate_rut(self, value):
        valor = value.strip().upper()
        if not re.fullmatch(r'\d{1,2}\.\d{3}\.\d{3}-[0-9K]', valor):
            raise serializers.ValidationError('RUT con puntos y guion: 76.123.456-7.')
        return valor

    def validate_anio(self, value):
        if not 2000 <= value <= 2100:
            raise serializers.ValidationError('El año debe estar entre 2000 y 2100.')
        return value

    def validate_monto(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('El monto debe ser positivo.')
        return value

    def validate_factor(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('El factor debe ser positivo.')
        return value

    def validate(self, attrs):
        rut = attrs.get('rut', getattr(self.instance, 'rut', None))
        anio = attrs.get('anio', getattr(self.instance, 'anio', None))
        repetidos = Calificacion.objects.filter(rut=rut, anio=anio)
        if self.instance:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise serializers.ValidationError({'rut': ['Ya existe una calificación para ese RUT y año.']})
        return attrs